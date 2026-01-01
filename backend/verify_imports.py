import os
import sys
import importlib.util
import traceback

# Add backend root to path
BACKEND_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BACKEND_ROOT)

def verify_file(filepath):
    """
    Attempts to compile and import a python file.
    """
    rel_path = os.path.relpath(filepath, BACKEND_ROOT)
    module_name = rel_path.replace(".py", "").replace(os.sep, ".")
    
    print(f"Checking {rel_path} ... ", end="")
    
    try:
        # 1. Syntax Check (Compile)
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        compile(source, filepath, 'exec')
        
        # 2. Import Check
        # Skip tests or scripts that might run immediately on import
        if "tests" in rel_path or "verify" in rel_path:
            print("OK (Syntax Only)")
            return True

        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
        print("OK")
        return True
    
    except SyntaxError as e:
        print("FAIL (SyntaxError)")
        print(f"  Line {e.lineno}: {e.text}")
        return False
    except ImportError as e:
        print(f"FAIL (ImportError: {e})")
        return False
    except Exception as e:
        print(f"FAIL (Runtime Error: {e})")
        traceback.print_exc()
        return False

def verify_all():
    failed = []
    for root, dirs, files in os.walk(BACKEND_ROOT):
        if "venv" in root or "__pycache__" in root:
            continue
            
        for file in files:
            if file.endswith(".py") and file != "verify_imports.py":
                path = os.path.join(root, file)
                if not verify_file(path):
                    failed.append(path)
                    
    if failed:
        print("\n❌ Verification Failed for files:")
        for f in failed:
            print(f" - {f}")
        sys.exit(1)
    else:
        print("\n✅ All files verified successfully.")
        sys.exit(0)

if __name__ == "__main__":
    verify_all()
