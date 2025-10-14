import pyvisa

# Use the pure Python backend (no drivers)
rm = pyvisa.ResourceManager('@py')

print("Connected VISA instruments:")
devices = rm.list_resources()
print(devices)

if not devices:
    print("No instruments found. Check USB/LAN connection.")
else:
    # Replace with your device's address from the list
    dl = rm.open_resource(devices[0])
    print("Connected to:", dl.query("*IDN?"))
    dl.close()