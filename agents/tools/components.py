import json

# 初始化workspace/components.json
def initialize_components_json():
    with open('workspace/components.json', 'w') as f:
        json.dump({'metadata': {'version': '1.0', 'last_updated': '2026-03-10'}, 'projects': {}}, f)