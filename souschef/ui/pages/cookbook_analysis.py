"""Cookbook Analysis Page for SousChef UI."""

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
import sys
import os

# Add the parent directory to the path so we can import souschef modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from souschef.parsers.metadata import read_cookbook_metadata
from souschef.assessment import assess_chef_migration_complexity


def show_cookbook_analysis_page():
    """Show the cookbook analysis page."""
    st.header("Cookbook Analysis")

    # Cookbook path input
    cookbook_path = st.text_input(
        "Cookbook Directory Path",
        placeholder="/path/to/your/cookbooks",
        help="Enter the absolute path to your Chef cookbooks directory"
    )

    if cookbook_path:
        if Path(cookbook_path).exists():
            st.success(f"Found directory: {cookbook_path}")

            # List cookbooks
            try:
                cookbooks = [d for d in Path(cookbook_path).iterdir() if d.is_dir()]
                if cookbooks:
                    st.subheader("Available Cookbooks")

                    # Create a dataframe for display
                    cookbook_data = []
                    for cookbook in cookbooks:
                        metadata_file = cookbook / "metadata.rb"
                        if metadata_file.exists():
                            try:
                                metadata = read_cookbook_metadata(str(metadata_file))
                                # Parse metadata for key info
                                name = metadata.get("name", cookbook.name)
                                version = metadata.get("version", "Unknown")
                                maintainer = metadata.get("maintainer", "Unknown")
                                description = metadata.get("description", "No description")
                                dependencies = len(metadata.get("depends", []))

                                cookbook_data.append({
                                    "Name": name,
                                    "Version": version,
                                    "Maintainer": maintainer,
                                    "Description": description[:50] + "..." if len(description) > 50 else description,
                                    "Dependencies": dependencies,
                                    "Path": str(cookbook),
                                    "Has Metadata": "Yes"
                                })
                            except Exception as e:
                                cookbook_data.append({
                                    "Name": cookbook.name,
                                    "Version": "Error",
                                    "Maintainer": "Error",
                                    "Description": f"Parse error: {str(e)[:50]}",
                                    "Dependencies": 0,
                                    "Path": str(cookbook),
                                    "Has Metadata": "No"
                                })
                        else:
                            cookbook_data.append({
                                "Name": cookbook.name,
                                "Version": "No metadata",
                                "Maintainer": "Unknown",
                                "Description": "No metadata.rb found",
                                "Dependencies": 0,
                                "Path": str(cookbook),
                                "Has Metadata": "❌"
                            })

                    df = pd.DataFrame(cookbook_data)
                    st.dataframe(df, use_container_width=True)

                    # Analysis actions
                    selected_cookbooks = st.multiselect(
                        "Select cookbooks to analyze",
                        [cb["Name"] for cb in cookbook_data if cb["Has Metadata"] == "Yes"]
                    )

                    if selected_cookbooks and st.button("Analyze Selected Cookbooks", type="primary"):
                        analyze_selected_cookbooks(cookbook_path, selected_cookbooks)

                else:
                    st.warning("No subdirectories found in the specified path. Are these individual cookbooks?")

            except Exception as e:
                st.error(f"Error reading directory: {e}")

        else:
            st.error(f"Directory not found: {cookbook_path}")

    # Instructions
    with st.expander("How to Use"):
        st.markdown("""
        1. **Enter Cookbook Path**: Provide the absolute path to your cookbooks directory
        2. **Review Cookbooks**: The interface will list all cookbooks with metadata
        3. **Select Cookbooks**: Choose which cookbooks to analyze
        4. **Run Analysis**: Click "Analyze Selected Cookbooks" to get detailed insights

        **Expected Structure:**
        ```
        /path/to/cookbooks/
        ├── nginx/
        │   ├── metadata.rb
        │   ├── recipes/
        │   └── attributes/
        ├── apache2/
        │   └── metadata.rb
        └── mysql/
            └── metadata.rb
        ```
        """)


def analyze_selected_cookbooks(cookbook_path: str, selected_cookbooks: List[str]):
    """Analyze the selected cookbooks and display results."""
    st.subheader("🔬 Analysis Results")

    progress_bar = st.progress(0)
    status_text = st.empty()

    results = []
    total = len(selected_cookbooks)

    for i, cookbook_name in enumerate(selected_cookbooks):
        status_text.text(f"Analyzing {cookbook_name}... ({i+1}/{total})")
        progress_bar.progress((i + 1) / total)

        # Find the cookbook directory
        cookbook_dir = None
        for d in Path(cookbook_path).iterdir():
            if d.is_dir() and d.name == cookbook_name:
                cookbook_dir = d
                break

        if cookbook_dir:
            try:
                # Assess migration complexity
                assessment = assess_chef_migration_complexity(str(cookbook_dir))

                # Read metadata
                metadata = read_cookbook_metadata(str(cookbook_dir / "metadata.rb"))

                # Basic analysis
                analysis = {
                    "name": cookbook_name,
                    "path": str(cookbook_dir),
                    "version": metadata.get("version", "Unknown"),
                    "maintainer": metadata.get("maintainer", "Unknown"),
                    "description": metadata.get("description", "No description"),
                    "dependencies": len(metadata.get("depends", [])),
                    "complexity": assessment.get("complexity", "Unknown"),
                    "estimated_hours": assessment.get("estimated_hours", 0),
                    "recommendations": assessment.get("recommendations", ""),
                    "status": "✅ Analyzed"
                }

                results.append(analysis)

            except Exception as e:
                results.append({
                    "name": cookbook_name,
                    "path": str(cookbook_dir),
                    "version": "Error",
                    "maintainer": "Error",
                    "description": f"Analysis failed: {e}",
                    "dependencies": 0,
                    "complexity": "Error",
                    "estimated_hours": 0,
                    "recommendations": f"Error: {e}",
                    "status": "❌ Failed"
                })

    progress_bar.empty()
    status_text.empty()

    # Display results
    if results:
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            successful = len([r for r in results if r["status"] == "✅ Analyzed"])
            st.metric("Successfully Analyzed", f"{successful}/{total}")

        with col2:
            total_hours = sum(r.get("estimated_hours", 0) for r in results)
            st.metric("Total Estimated Hours", f"{total_hours:.1f}")

        with col3:
            complexities = [r.get("complexity", "Unknown") for r in results]
            high_complexity = complexities.count("High")
            st.metric("High Complexity Cookbooks", high_complexity)

        # Results table
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True)

        # Detailed analysis
        st.subheader("📊 Detailed Analysis")

        for result in results:
            if result["status"] == "✅ Analyzed":
                with st.expander(f"📖 {result['name']} - {result['complexity']} Complexity"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Version:** {result['version']}")
                        st.write(f"**Maintainer:** {result['maintainer']}")
                        st.write(f"**Dependencies:** {result['dependencies']}")

                    with col2:
                        st.write(f"**Estimated Hours:** {result['estimated_hours']:.1f}")
                        st.write(f"**Complexity:** {result['complexity']}")

                    st.write(f"**Recommendations:** {result['recommendations']}")

        # Download option
        if successful > 0:
            st.download_button(
                label="📥 Download Analysis Report",
                data=pd.DataFrame(results).to_json(indent=2),
                file_name="cookbook_analysis.json",
                mime="application/json",
                help="Download the analysis results as JSON"
            )


if __name__ == "__main__":
    show_cookbook_analysis_page()
