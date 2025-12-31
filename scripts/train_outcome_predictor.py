import sys
import os
import csv
import json
import pickle

# Add backend to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model_dir = os.path.join(project_root, "backend", "models", "outcome_predictor")
data_file = os.path.join(project_root, "data", "prediction_dataset.csv")

def train_predictor():
    print("Training Outcome Predictor...")
    
    if not os.path.exists(data_file):
        print("Dataset not found. Run scripts/export_prediction_dataset.py first.")
        return
        
    features = []
    labels = []
    feature_names = []
    
    try:
        with open(data_file, "r") as f:
            reader = csv.DictReader(f)
            feature_names = [f for f in reader.fieldnames if f not in ["session_id", "target_label"]]
            
            for row in reader:
                vec = [float(row[k]) for k in feature_names]
                features.append(vec)
                labels.append(int(row["target_label"]))
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return
            
    if len(features) < 2:
        print("Not enough data to train (need at least 2 samples).")
        # Save dummy
        os.makedirs(model_dir, exist_ok=True)
        with open(os.path.join(model_dir, "model.pkl"), "wb") as f:
            pickle.dump({"dummy": True, "note": "insufficient_data"}, f)
        with open(os.path.join(model_dir, "features.json"), "w") as f:
            json.dump(feature_names, f)
        print("Saved DUMMY model artifacts.")
        return

    # 2. Train
    try:
        import joblib
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        import numpy as np
        
        X = np.array(features)
        y = np.array(labels)
        
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('clf', LogisticRegression(class_weight='balanced'))
        ])
        
        pipeline.fit(X, y)
        print("Model trained successfully.")
        
        # 3. Save Artifacts
        os.makedirs(model_dir, exist_ok=True)
        
        joblib.dump(pipeline, os.path.join(model_dir, "model.pkl"))
        
        # Save feature columns for runtime builder to ensure order
        with open(os.path.join(model_dir, "features.json"), "w") as f:
            json.dump(feature_names, f)
            
        print(f"Model saved to {model_dir}")
        
    except ImportError:
        print("scikit-learn or joblib not found. Saving dummy artifacts.")
        os.makedirs(model_dir, exist_ok=True)
        with open(os.path.join(model_dir, "model.pkl"), "wb") as f:
            pickle.dump({"dummy": True, "note": "missing_deps"}, f)
        with open(os.path.join(model_dir, "features.json"), "w") as f:
            json.dump(feature_names, f)

if __name__ == "__main__":
    train_predictor()
