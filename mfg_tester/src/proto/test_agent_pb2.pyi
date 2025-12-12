from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class LogLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LOG_LEVEL_UNSPECIFIED: _ClassVar[LogLevel]
    LOG_LEVEL_DEBUG: _ClassVar[LogLevel]
    LOG_LEVEL_INFO: _ClassVar[LogLevel]
    LOG_LEVEL_WARN: _ClassVar[LogLevel]
    LOG_LEVEL_ERROR: _ClassVar[LogLevel]
    LOG_LEVEL_FATAL: _ClassVar[LogLevel]
LOG_LEVEL_UNSPECIFIED: LogLevel
LOG_LEVEL_DEBUG: LogLevel
LOG_LEVEL_INFO: LogLevel
LOG_LEVEL_WARN: LogLevel
LOG_LEVEL_ERROR: LogLevel
LOG_LEVEL_FATAL: LogLevel

class GetAgentDetailsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetAgentDetailsResponse(_message.Message):
    __slots__ = ("agent_version", "device_id", "mac_addr", "ip_addr")
    AGENT_VERSION_FIELD_NUMBER: _ClassVar[int]
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    MAC_ADDR_FIELD_NUMBER: _ClassVar[int]
    IP_ADDR_FIELD_NUMBER: _ClassVar[int]
    agent_version: str
    device_id: str
    mac_addr: str
    ip_addr: str
    def __init__(self, agent_version: _Optional[str] = ..., device_id: _Optional[str] = ..., mac_addr: _Optional[str] = ..., ip_addr: _Optional[str] = ...) -> None: ...

class OLEDSettings(_message.Message):
    __slots__ = ("I2CBusName", "DevAddr", "Width", "Height", "PowerPin", "ResetPin")
    I2CBUSNAME_FIELD_NUMBER: _ClassVar[int]
    DEVADDR_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    POWERPIN_FIELD_NUMBER: _ClassVar[int]
    RESETPIN_FIELD_NUMBER: _ClassVar[int]
    I2CBusName: str
    DevAddr: int
    Width: int
    Height: int
    PowerPin: int
    ResetPin: int
    def __init__(self, I2CBusName: _Optional[str] = ..., DevAddr: _Optional[int] = ..., Width: _Optional[int] = ..., Height: _Optional[int] = ..., PowerPin: _Optional[int] = ..., ResetPin: _Optional[int] = ...) -> None: ...

class SetOLEDTextRequest(_message.Message):
    __slots__ = ("text",)
    TEXT_FIELD_NUMBER: _ClassVar[int]
    text: str
    def __init__(self, text: _Optional[str] = ...) -> None: ...

class BatterySettings(_message.Message):
    __slots__ = ("device_name", "voltage_node", "current_node", "temp_node")
    DEVICE_NAME_FIELD_NUMBER: _ClassVar[int]
    VOLTAGE_NODE_FIELD_NUMBER: _ClassVar[int]
    CURRENT_NODE_FIELD_NUMBER: _ClassVar[int]
    TEMP_NODE_FIELD_NUMBER: _ClassVar[int]
    device_name: str
    voltage_node: str
    current_node: str
    temp_node: str
    def __init__(self, device_name: _Optional[str] = ..., voltage_node: _Optional[str] = ..., current_node: _Optional[str] = ..., temp_node: _Optional[str] = ...) -> None: ...

class GetBatteryReadingsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetBatteryReadingsResponse(_message.Message):
    __slots__ = ("millivolts", "milliamps", "celsius_temperature", "present", "status")
    MILLIVOLTS_FIELD_NUMBER: _ClassVar[int]
    MILLIAMPS_FIELD_NUMBER: _ClassVar[int]
    CELSIUS_TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    PRESENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    millivolts: float
    milliamps: float
    celsius_temperature: float
    present: bool
    status: str
    def __init__(self, millivolts: _Optional[float] = ..., milliamps: _Optional[float] = ..., celsius_temperature: _Optional[float] = ..., present: bool = ..., status: _Optional[str] = ...) -> None: ...

class EventDevice(_message.Message):
    __slots__ = ("device_name", "device_path", "device_type", "sysfs_path")
    DEVICE_NAME_FIELD_NUMBER: _ClassVar[int]
    DEVICE_PATH_FIELD_NUMBER: _ClassVar[int]
    DEVICE_TYPE_FIELD_NUMBER: _ClassVar[int]
    SYSFS_PATH_FIELD_NUMBER: _ClassVar[int]
    device_name: str
    device_path: str
    device_type: str
    sysfs_path: str
    def __init__(self, device_name: _Optional[str] = ..., device_path: _Optional[str] = ..., device_type: _Optional[str] = ..., sysfs_path: _Optional[str] = ...) -> None: ...

class GetEventReportOverDurationRequest(_message.Message):
    __slots__ = ("device_path", "duration_seconds")
    DEVICE_PATH_FIELD_NUMBER: _ClassVar[int]
    DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
    device_path: str
    duration_seconds: int
    def __init__(self, device_path: _Optional[str] = ..., duration_seconds: _Optional[int] = ...) -> None: ...

class GetEventReportOverDurationResponse(_message.Message):
    __slots__ = ("csv_report",)
    CSV_REPORT_FIELD_NUMBER: _ClassVar[int]
    csv_report: str
    def __init__(self, csv_report: _Optional[str] = ...) -> None: ...

class DiscoverEventDevicesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DiscoverEventDevicesResponse(_message.Message):
    __slots__ = ("devices",)
    DEVICES_FIELD_NUMBER: _ClassVar[int]
    devices: _containers.RepeatedCompositeFieldContainer[EventDevice]
    def __init__(self, devices: _Optional[_Iterable[_Union[EventDevice, _Mapping]]] = ...) -> None: ...

class BuzzerSettings(_message.Message):
    __slots__ = ("device_path",)
    DEVICE_PATH_FIELD_NUMBER: _ClassVar[int]
    device_path: str
    def __init__(self, device_path: _Optional[str] = ...) -> None: ...

class SetBuzzerRequest(_message.Message):
    __slots__ = ("on",)
    ON_FIELD_NUMBER: _ClassVar[int]
    on: bool
    def __init__(self, on: bool = ...) -> None: ...

class GetSystemStateRequest(_message.Message):
    __slots__ = ("idle_duration_seconds", "cpu_temperature_sysfs_path")
    IDLE_DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
    CPU_TEMPERATURE_SYSFS_PATH_FIELD_NUMBER: _ClassVar[int]
    idle_duration_seconds: int
    cpu_temperature_sysfs_path: str
    def __init__(self, idle_duration_seconds: _Optional[int] = ..., cpu_temperature_sysfs_path: _Optional[str] = ...) -> None: ...

class GetSystemStateResponse(_message.Message):
    __slots__ = ("serial", "cpu_temperature", "cpu_idle_percent", "total_memory_kb", "cpu_load_average")
    SERIAL_FIELD_NUMBER: _ClassVar[int]
    CPU_TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    CPU_IDLE_PERCENT_FIELD_NUMBER: _ClassVar[int]
    TOTAL_MEMORY_KB_FIELD_NUMBER: _ClassVar[int]
    CPU_LOAD_AVERAGE_FIELD_NUMBER: _ClassVar[int]
    serial: str
    cpu_temperature: float
    cpu_idle_percent: float
    total_memory_kb: int
    cpu_load_average: float
    def __init__(self, serial: _Optional[str] = ..., cpu_temperature: _Optional[float] = ..., cpu_idle_percent: _Optional[float] = ..., total_memory_kb: _Optional[int] = ..., cpu_load_average: _Optional[float] = ...) -> None: ...

class UploadFileRequest(_message.Message):
    __slots__ = ("filename", "chunk_data", "offset", "total_size")
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    CHUNK_DATA_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    TOTAL_SIZE_FIELD_NUMBER: _ClassVar[int]
    filename: str
    chunk_data: bytes
    offset: int
    total_size: int
    def __init__(self, filename: _Optional[str] = ..., chunk_data: _Optional[bytes] = ..., offset: _Optional[int] = ..., total_size: _Optional[int] = ...) -> None: ...

class UploadFileResponse(_message.Message):
    __slots__ = ("message", "success")
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    message: str
    success: bool
    def __init__(self, message: _Optional[str] = ..., success: bool = ...) -> None: ...

class DownloadFileRequest(_message.Message):
    __slots__ = ("filename",)
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    filename: str
    def __init__(self, filename: _Optional[str] = ...) -> None: ...

class DownloadFileResponse(_message.Message):
    __slots__ = ("chunk_data", "offset", "total_size")
    CHUNK_DATA_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    TOTAL_SIZE_FIELD_NUMBER: _ClassVar[int]
    chunk_data: bytes
    offset: int
    total_size: int
    def __init__(self, chunk_data: _Optional[bytes] = ..., offset: _Optional[int] = ..., total_size: _Optional[int] = ...) -> None: ...

class RunCommandRequest(_message.Message):
    __slots__ = ("command", "args", "timeout_seconds", "working_directory", "stdin_data", "use_shell")
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    ARGS_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_SECONDS_FIELD_NUMBER: _ClassVar[int]
    WORKING_DIRECTORY_FIELD_NUMBER: _ClassVar[int]
    STDIN_DATA_FIELD_NUMBER: _ClassVar[int]
    USE_SHELL_FIELD_NUMBER: _ClassVar[int]
    command: str
    args: _containers.RepeatedScalarFieldContainer[str]
    timeout_seconds: int
    working_directory: str
    stdin_data: str
    use_shell: bool
    def __init__(self, command: _Optional[str] = ..., args: _Optional[_Iterable[str]] = ..., timeout_seconds: _Optional[int] = ..., working_directory: _Optional[str] = ..., stdin_data: _Optional[str] = ..., use_shell: bool = ...) -> None: ...

class RunCommandResponse(_message.Message):
    __slots__ = ("exit_code", "stdout", "stderr", "error_message")
    EXIT_CODE_FIELD_NUMBER: _ClassVar[int]
    STDOUT_FIELD_NUMBER: _ClassVar[int]
    STDERR_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    exit_code: int
    stdout: str
    stderr: str
    error_message: str
    def __init__(self, exit_code: _Optional[int] = ..., stdout: _Optional[str] = ..., stderr: _Optional[str] = ..., error_message: _Optional[str] = ...) -> None: ...

class GetDeviceInfoRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetDeviceInfoResponse(_message.Message):
    __slots__ = ("device_id", "custom_fields")
    class CustomFieldsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_FIELDS_FIELD_NUMBER: _ClassVar[int]
    device_id: str
    custom_fields: _containers.ScalarMap[str, str]
    def __init__(self, device_id: _Optional[str] = ..., custom_fields: _Optional[_Mapping[str, str]] = ...) -> None: ...

class StreamExecutionLogsRequest(_message.Message):
    __slots__ = ("min_level", "component_filter", "follow")
    MIN_LEVEL_FIELD_NUMBER: _ClassVar[int]
    COMPONENT_FILTER_FIELD_NUMBER: _ClassVar[int]
    FOLLOW_FIELD_NUMBER: _ClassVar[int]
    min_level: LogLevel
    component_filter: str
    follow: bool
    def __init__(self, min_level: _Optional[_Union[LogLevel, str]] = ..., component_filter: _Optional[str] = ..., follow: bool = ...) -> None: ...

class LogEntry(_message.Message):
    __slots__ = ("timestamp", "level", "component", "message")
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    COMPONENT_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    timestamp: str
    level: LogLevel
    component: str
    message: str
    def __init__(self, timestamp: _Optional[str] = ..., level: _Optional[_Union[LogLevel, str]] = ..., component: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...
