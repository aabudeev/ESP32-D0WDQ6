from board import DeviceInfo

device = DeviceInfo()
print("System Info:")
for key, value in device.get_system_info().items():
    print(f"  {key}: {value}")
