import urllib.request
import hashlib
import ssl
from pathlib import Path

urls = [
    ("Rajdhani_Exp.pdf", "https://indianrailways.gov.in/railwayboard/uploads/directorate/coaching/TAG_2023-24/Rajdhani_Exp.pdf", "data/raw/timetables/Rajdhani_Exp.pdf"),
    ("Shatabdi_Exp.pdf", "https://indianrailways.gov.in/railwayboard/uploads/directorate/coaching/TAG_2023-24/Shatabdi_Exp.pdf", "data/raw/timetables/Shatabdi_Exp.pdf"),
    ("Duronto_Exp.pdf", "https://indianrailways.gov.in/railwayboard/uploads/directorate/coaching/TAG_2023-24/Duronto_Exp.pdf", "data/raw/timetables/Duronto_Exp.pdf"),
    ("Vande_Tejas_Uday_Gatiman_Exp.pdf", "https://indianrailways.gov.in/railwayboard/uploads/directorate/coaching/TAG_2023-24/Vande_Tejas_Uday_Gatiman_Exp.pdf", "data/raw/timetables/Vande_Tejas_Uday_Gatiman_Exp.pdf"),
    ("Train_Number_Index.pdf", "https://indianrailways.gov.in/railwayboard/uploads/directorate/coaching/TAG_2023-24/Train_Number_Index.pdf", "data/raw/timetables/Train_Number_Index.pdf"),
    ("Train_Name_Index.pdf", "https://indianrailways.gov.in/railwayboard/uploads/directorate/coaching/TAG_2023-24/Train_Name_Index.pdf", "data/raw/timetables/Train_Name_Index.pdf"),
    ("How_to_Read_Table.pdf", "https://indianrailways.gov.in/railwayboard/uploads/directorate/coaching/TAG_2023-24/how2read.pdf", "data/raw/timetables/how2read.pdf")
]

import subprocess

for name, url, out_path in urls:
    p = Path(out_path)
    if not p.exists() or p.stat().st_size == 0:
        print(f"Downloading {name}...")
        cmd = ["curl.exe", "-k", "-s", url, "-o", str(p)]
        subprocess.run(cmd, check=True)
    if p.exists():
        size = p.stat().st_size
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        print(f"{name}: {size} bytes, sha256={sha[:12]}...")
