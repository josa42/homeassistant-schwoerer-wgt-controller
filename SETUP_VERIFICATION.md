# Setup Verification

## Initial Config Flow

### Steps:
1. **Discovery Phase**
   - Integration discovers all `schwoerer_lueftung` entities
   - Identifies rooms via `room_number` attribute
   - Validates: rooms found, outdoor temp sensor found
   - Extracts room and main device identifiers

2. **User Confirmation**
   - Shows list of discovered rooms
   - User clicks "Submit" to confirm
   - No additional input required

3. **Entry Creation**
   - Creates entry with:
     - `test_mode`: false
     - `rooms`: dict with room configs
   - All rooms automatically configured

### Built-in Entities Created:
- `switch.xxx_controller_enabled` - Enable/disable controller
- `switch.xxx_test_mode` - Test mode toggle
- `switch.xxx_vacation_mode` - Vacation mode
- `switch.xxx_heating_lock` - Heating lock
- `select.xxx_fan_level_override` - Fan level override (Auto, 0-4)

### Sensors Created (per room):
- `sensor.xxx_room_N_mode` - Current mode
- `sensor.xxx_room_N_target_temp` - Target temperature
- `sensor.xxx_room_N_explanation` - Why current settings

### Global Sensors:
- `sensor.xxx_controller_status` - Overall status
- `sensor.xxx_controller_explanation` - Global explanation
- `binary_sensor.xxx_heating_release` - Heat pump heating state
- `binary_sensor.xxx_cooling_release` - Heat pump cooling state
- `binary_sensor.xxx_night_mode` - Night mode active
- `binary_sensor.xxx_vacation_mode` - Vacation mode active

## Device Attachment:
- Global entities → schwoerer_lueftung main device
- Room entities → schwoerer_lueftung room devices
- Uses `room_number` attribute (language-independent)

## Options Flow:
After setup, configure via Options:
- General: Test mode
- Temperatures: Normal, Night, Vacation, Window open
- Timing: Night mode hours, window delay
- Fan Levels: Normal, Night, Vacation, High humidity
- Thresholds: Outdoor temp, humidity threshold, humidity sensor
- Rooms: Per-room temperatures, window sensors, floor assignment

## Current Status:
✓ Config flow tested and working
✓ Discovery finds 6 rooms
✓ Test mode enabled (no actual changes)
✓ All entities created successfully
✓ Device attachment working
✓ Room number attribute used (not entity_id parsing)
