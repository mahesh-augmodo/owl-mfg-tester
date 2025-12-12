import openhtf as htf
from openhtf.util.configuration import CONF
import yaml


def apply_limits_to_test(test_instance, file_path):
    """
    Reads CONF.limits and applies them to the measurements in the provided Test instance.
    """
    with open(file_path, "r") as limits_file:
        limits_config = yaml.full_load(limits_file)

    if not limits_config:
        print("Warning: No 'limits' found in configuration.")
        return

    # 1. Correctly access all phases from the Test instance
    # Test -> TestDescriptor -> PhaseSequence -> all_phases()
    phases = test_instance.descriptor.phase_sequence.all_phases()

    # 2. Iterate through every phase
    for phase in phases:
        # 3. Iterate through measurements defined on that phase
        for measurement in phase.measurements:

            # Check if this measurement name exists in our config
            if measurement.name in limits_config:
                limit_data = limits_config[measurement.name]

                # Apply Unit
                if 'unit' in limit_data:
                    # Resolve string "SECOND" to htf.units.SECOND if possible
                    unit_str = limit_data['unit']
                    unit_val = getattr(htf.units, unit_str, unit_str)
                    measurement.with_units(unit_val)

                # Apply Range
                min_val = limit_data.get('min')
                max_val = limit_data.get('max')

                # Apply Boolean (equals) validation
                equals_val = limit_data.get('equals')

                # OpenHTF validators are additive, so we clear old ones if you want
                # (Optional: usually not needed if the code definition has none)
                # measurement.validators = []

                if min_val is not None and max_val is not None:
                    measurement.in_range(min_val, max_val)
                elif min_val is not None:
                    # "Greater than or equal to min"
                    measurement.in_range(min_val, float('inf'))
                elif max_val is not None:
                    # "Less than or equal to max"
                    measurement.in_range(float('-inf'), max_val)
                elif equals_val is not None:
                    # Apply boolean 'equals' validation
                    measurement.equals(equals_val)

                # Apply Docstring
                if 'doc' in limit_data:
                    measurement.doc(limit_data['doc'])
