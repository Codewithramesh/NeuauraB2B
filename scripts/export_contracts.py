"""Export the actual runtime schemas; no hand-maintained duplicate API types."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.main import create_app
from backend.app.schemas import Extraction
from backend.app.config import ROOT
folder=ROOT/'shared/api-contracts'
folder.mkdir(parents=True,exist_ok=True)
(folder/'openapi.json').write_text(json.dumps(create_app().openapi(),indent=2)+'\n')
(folder/'extraction.schema.json').write_text(json.dumps(Extraction.model_json_schema(),indent=2)+'\n')
print('Exported OpenAPI and extraction schemas.')
