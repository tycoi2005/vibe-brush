import json
import re

path = "/tmp/ob_config.cfg"
try:
    with open(path, "r") as f:
        content = f.read()

    # Open Brush config sometimes has trailing commas
    content = re.sub(r",\s*}", "}", content)
    content = re.sub(r",\s*\]", "]", content)

    config = json.loads(content)
except Exception as e:
    print(f"Error reading config: {e}")
    config = {
        "Flags": {
            "EnableMonoscopicMode": True,
            "EnableApiRemoteCalls": True,
            "EnableApiCorsHeaders": True
        }
    }

if "Export" not in config:
    config["Export"] = {}

config["Export"]["Formats"] = {
    "fbx": True,
    "glb": True,
    "gltf": True,
    "obj": True,
    "json": True
}

with open("/tmp/ob_config_updated.cfg", "w") as f:
    json.dump(config, f, indent=2)

print("Updated config written to /tmp/ob_config_updated.cfg")
