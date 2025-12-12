import sys
from openhtf.output.callbacks import console_summary
from openhtf.core import test_record


class VerboseConsoleSummary(console_summary.ConsoleSummary):
    """Prints a full table of all phases, even if the test Passed.
        ConsoleSummary only prints table on failure.
    """

    def __call__(self, record: test_record.TestRecord) -> None:
        if record is None:
            return

        # 1. Print Header
        self.output_stream.write("\n" + "=" * 50 + "\n")

        # Colorize the main outcome
        color = self.color_table.get(record.outcome, self.RESET)
        outcome_str = f"{color}{record.outcome.name}{self.RESET}"

        self.output_stream.write(
            f"TEST RESULT: {outcome_str} | DUT: {
                record.dut_id}\n")
        self.output_stream.write("=" * 50 + "\n")
        self.output_stream.write(f"{'Phase Name':<35} | {'Outcome':<10}\n")
        self.output_stream.write("-" * 50 + "\n")

        # 2. Iterate through ALL phases (No 'if failed' check!)
        for phase in record.phases:
            if phase.name == 'trigger_phase':
                continue

            # Determine Color/Icon
            p_outcome = phase.outcome.name if phase.outcome else "UNKNOWN"

            if p_outcome == 'PASS':
                p_color = self.GREEN
                icon = "OK"
            else:
                p_color = self.RED
                icon = "XX"

            # Print the row
            self.output_stream.write(
                f"{p_color}{icon} {phase.name:<32} | {p_outcome}{self.RESET}\n"
            )

            # 3. If failed, print details (copied from your original logic)
            if p_outcome != 'PASS' and phase.result:
                error_msg = phase.result.phase_result
                self.output_stream.write(f"   └── Reason: {error_msg}\n")

        self.output_stream.write("=" * 50 + "\n\n")
        self.output_stream.flush()
