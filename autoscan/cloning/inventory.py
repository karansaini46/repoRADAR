import os
from pathlib import Path
from typing import Dict, Any, List

class RepoInventory:
    def __init__(self):
        self.skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "vendor"}
        
        self.ci_configs = {
            ".github/workflows", 
            ".gitlab-ci.yml", 
            "Jenkinsfile", 
            ".travis.yml", 
            "circle.yml", 
            ".circleci/config.yml"
        }
        
        self.manifest_names = {
            "package.json", 
            "requirements.txt", 
            "Pipfile", 
            "pyproject.toml", 
            "pom.xml", 
            "build.gradle", 
            "go.mod", 
            "Cargo.toml",
            "Gemfile"
        }

    def scan(self, local_path: Path) -> Dict[str, Any]:
        """
        Scans a local repository directory and returns inventory metrics.
        """
        result = {
            "file_count": 0,
            "total_size_mb": 0.0,
            "languages": {},
            "has_dockerfile": False,
            "has_ci_config": False,
            "has_env_example": False,
            "package_manifests": [],
            "secret_patterns_present": False,
            "top_level_files": []
        }
        
        if not local_path.exists() or not local_path.is_dir():
            return result
            
        total_size_bytes = 0
        
        # Get top level files
        try:
            for item in local_path.iterdir():
                if item.is_file():
                    result["top_level_files"].append(item.name)
        except Exception:
            pass

        for root, dirs, files in os.walk(local_path):
            # Modify dirs in-place to skip specific directories
            dirs[:] = [d for d in dirs if d not in self.skip_dirs]
            
            root_path = Path(root)
            rel_root = root_path.relative_to(local_path)
            
            # Check for CI configs in directories (e.g., .github/workflows)
            if not result["has_ci_config"]:
                rel_root_str = str(rel_root).replace("\\", "/")
                if rel_root_str in self.ci_configs:
                    result["has_ci_config"] = True
            
            for file in files:
                file_path = root_path / file
                
                # Update file count and size
                result["file_count"] += 1
                try:
                    total_size_bytes += file_path.stat().st_size
                except Exception:
                    pass
                    
                # Language by extension
                ext = file_path.suffix.lower()
                if ext:
                    result["languages"][ext] = result["languages"].get(ext, 0) + 1
                    
                # Specific files check
                name_lower = file.lower()
                
                if name_lower == "dockerfile" or name_lower.endswith(".dockerfile"):
                    result["has_dockerfile"] = True
                    
                if file in self.manifest_names:
                    # Store relative path of manifest
                    rel_path = file_path.relative_to(local_path)
                    result["package_manifests"].append(str(rel_path))
                    
                if file == ".env.example" or file == "env.example":
                    result["has_env_example"] = True
                    
                # Naive secrets check
                if file == ".env" or file.endswith(".pem") or file == "id_rsa":
                    result["secret_patterns_present"] = True
                    
                # Check for CI files that are at root
                if not result["has_ci_config"]:
                    rel_path_str = str(file_path.relative_to(local_path)).replace("\\", "/")
                    if rel_path_str in self.ci_configs:
                        result["has_ci_config"] = True
                        
        result["total_size_mb"] = round(total_size_bytes / (1024 * 1024), 2)
        
        return result
