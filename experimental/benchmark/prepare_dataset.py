import os
import subprocess
import json

SAMPLE_AUDIO_DIR = os.path.join("sample_audio")
DATASET_BASE = os.path.join("experimental", "benchmark", "dataset")

# The mapping derived from dataset investigation
CATEGORIES = {
    "meeting": [
        "meeting_short.mp3",
        "meeting_messy.mp3",
        "meeting_clear.mp3",
        "BuisinessMeeting.mp3",
        "0001_Business_English_Conversations_ESL_Business_Meeting_Conversation.m4a"
    ],
    "sales": [
        "sales_bad.mp3",
        "sales_ambiguous.mp3",
        "SalesMeeting.mp3",
        "sales_good.mp3"
    ],
    "interview": [
        "0001_Winner_Best_Pitch_Competition_Willy_Green_Party_on_Demand.m4a"
    ]
}

def convert_to_wav(input_path, output_path):
    # Converts to 16kHz Mono WAV
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ac", "1", "-ar", "16000",
        output_path
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True, ""
    except subprocess.CalledProcessError as e:
        return False, e.stderr.decode('utf-8', errors='replace')

def main():
    os.makedirs(DATASET_BASE, exist_ok=True)
    report = {
        "inventory": 0,
        "converted": 0,
        "skipped": 0,
        "failed": 0,
        "errors": []
    }
    
    for category, files in CATEGORIES.items():
        cat_dir = os.path.join(DATASET_BASE, category)
        os.makedirs(cat_dir, exist_ok=True)
        
        for f in files:
            input_path = os.path.join(SAMPLE_AUDIO_DIR, f)
            if not os.path.exists(input_path):
                print(f"File not found: {input_path}")
                continue
                
            report["inventory"] += 1
            filename_no_ext = os.path.splitext(f)[0]
            output_path = os.path.join(cat_dir, f"{filename_no_ext}.wav")
            
            if os.path.exists(output_path):
                print(f"Skipping (already exists): {output_path}")
                report["skipped"] += 1
                continue
                
            print(f"Converting {f} -> {output_path}...")
            success, err = convert_to_wav(input_path, output_path)
            if success:
                report["converted"] += 1
            else:
                print(f"Failed: {f} - {err}")
                report["failed"] += 1
                report["errors"].append((f, err))
                
    print("\n--- Dataset Preparation Report ---")
    print(json.dumps(report, indent=2))
    
    # Save the report for STOP GATE 1
    os.makedirs(os.path.join("experimental", "benchmark", "reports"), exist_ok=True)
    with open(os.path.join("experimental", "benchmark", "reports", "dataset_prep_report.json"), "w") as rf:
        json.dump(report, rf, indent=2)

if __name__ == "__main__":
    main()
