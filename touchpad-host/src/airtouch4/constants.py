"""AirTouch 4 protocol constants gathered from captures and APK findings."""

ADDR_MAIN_BOARD = 0x80
ADDR_TOUCHPAD_1 = 0x90
ADDR_TOUCHPAD_2 = 0x91
ADDR_TOUCHPAD_EXPANDED = 0x9F
ADDR_MOBILE = 0xB0
ADDR_SERVER = 0xC0

ADDRESS_NAMES = {
    ADDR_MAIN_BOARD: "main_board",
    ADDR_TOUCHPAD_1: "touchpad_1",
    ADDR_TOUCHPAD_2: "touchpad_2",
    ADDR_TOUCHPAD_EXPANDED: "touchpad_expanded",
    ADDR_MOBILE: "mobile_client",
    ADDR_SERVER: "server",
}

COMMAND_NAMES = {
    0x1F: "CMD_EXPANDED",
    0x20: "SET_GROUP_STATUS",
    0x21: "RESPONSE_GROUP_STATUS",
    0x22: "SET_AC_STATUS",
    0x23: "RESPONSE_AC_STATUS",
    0x24: "EXPANSION_DAMPER_STATUS",
    0x26: "SET_TEMPERATURE",
    0x27: "RESPONSE_LED",
    0x2A: "SET_GROUP_CONTROL_MOBILE",
    0x2B: "GROUP_STATUS_MOBILE",
    0x2C: "SET_AC_CONTROL_MOBILE",
    0x2D: "AC_STATUS_MOBILE",
    0x2F: "CLIENT_BULK_INFO",
    0x30: "SET_ACTIVE_FAVOURITE",
    0x31: "RESPONSE_ACTIVE_FAVOURITE",
    0x32: "SET_FAVOURITE",
    0x33: "RESPONSE_FAVOURITE",
    0x35: "RESPONSE_PROGRAM_DEFINE",
    0x36: "SET_AC_TIMER",
    0x37: "RESPONSE_AC_TIMER",
    0x3C: "SET_PROGRAM_DEFINE_NEW",
    0x3D: "RESPONSE_PROGRAM_DEFINE_NEW",
    0x40: "SET_DATETIME",
    0x41: "DATETIME_STATUS",
    0x43: "RESPONSE_AC_RUNTIME_STATUS",
    0x50: "SET_TURBO_GROUP",
    0x51: "RESPONSE_TURBO_GROUP",
    0x52: "SET_GROUP_NAME",
    0x53: "RESPONSE_GROUP_NAME",
    0x54: "SET_PREFERENCE",
    0x55: "RESPONSE_PREFERENCE",
    0x59: "RESPONSE_MAIN_DISPLAY_NEW",
    0x5B: "RESPONSE_MAIN_DISPLAY",
    0x5F: "RESPONSE_SETTING_DATA",
    0x60: "SET_PARAMETERS",
    0x61: "RESPONSE_PARAMETERS",
    0x62: "START_BALANCE",
    0x63: "RESPONSE_BALANCE",
    0x64: "STOP_BALANCE",
    0x66: "SET_GROUPING",
    0x67: "RESPONSE_GROUPING",
    0x68: "SET_SPILL",
    0x69: "RESPONSE_SPILL",
    0x6A: "SET_SERVICE",
    0x6B: "RESPONSE_SERVICE",
    0x6C: "SET_PASSWORD_INFO",
    0x6D: "RESPONSE_PASSWORD_INFO",
    0x6E: "CLEAR_NOTIFICATION",
    0x6F: "RESPONSE_DIALOG_MESSAGE",
    0x70: "SET_PAIR_SENSOR",
    0x71: "RESPONSE_SENSOR_LIST",
    0x72: "SET_SENSOR_TEMP",
    0x73: "RESPONSE_SENSOR_INFO",
    0x74: "SET_AC_BASE_INFO",
    0x75: "RESPONSE_AC_BASE_INFO",
    0x77: "RESPONSE_AC_SETTING",
    0x78: "SET_AC_SETTING_NEW",
    0x79: "RESPONSE_AC_SETTING_NEW",
    0x81: "RESPONSE_DEBUG_INFO",
    0x83: "RESPONSE_GATEWAY_INFO",
}


def address_name(address: int) -> str:
    if address in ADDRESS_NAMES:
        return ADDRESS_NAMES[address]
    high = address & 0xF0
    if high == 0x80:
        return "main_board_range"
    if high == 0x90:
        return "touchpad_range"
    if high == 0xB0:
        return "mobile_client_range"
    if high == 0xC0:
        return "server_range"
    if (address & 0xFC) == 0xFC:
        return "broadcast_or_expanded"
    return "unknown"


def command_name(command: int) -> str:
    return COMMAND_NAMES.get(command, "UNKNOWN")
