import sounddevice as sd

print("--- Output Devices ---")
devices = sd.query_devices()
output_devices = []
for idx, dev in enumerate(devices):
    if dev["max_output_channels"] > 0:
        api_name = sd.query_hostapis(dev["hostapi"])["name"]
        print(f"[{idx}] {dev['name']} ({api_name}) - Channels: {dev['max_output_channels']}")
        output_devices.append((idx, dev["name"]))

print(f"\nTotal output devices: {len(output_devices)}")
