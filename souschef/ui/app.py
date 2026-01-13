"""
Visual Migration Planning Interface for SousChef.

A Streamlit-based web interface for Chef to Ansible migration planning,
assessment, and visualization.
"""

import contextlib
import sys
from pathlib import Path

import streamlit as st

# Add the parent directory to the path so we can import souschef modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import page modules
from souschef.ui.pages.cookbook_analysis import show_cookbook_analysis_page


class ProgressTracker:
    """Track progress for long-running operations."""

    def __init__(self, total_steps=100, description="Processing..."):
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()

    def update(self, step=None, description=None):
        """Update progress."""
        if step is not None:
            self.current_step = min(step, self.total_steps)
        else:
            self.current_step = min(self.current_step + 1, self.total_steps)

        if description:
            self.description = description

        progress = min(self.current_step / self.total_steps, 1.0)
        self.progress_bar.progress(progress)
        self.status_text.text(
            f"{self.description} ({self.current_step}/{self.total_steps})"
        )

    def complete(self, message="Completed!"):
        """Mark progress as complete."""
        self.progress_bar.progress(1.0)
        self.status_text.text(message)
        import time

        time.sleep(0.5)  # Brief pause to show completion

    def close(self):
        """Clean up progress indicators."""
        self.progress_bar.empty()
        self.status_text.empty()


def with_progress_tracking(
    operation_func, description="Processing...", total_steps=100
):
    """Add progress tracking to operations."""

    def wrapper(*args, **kwargs):
        tracker = ProgressTracker(total_steps, description)
        try:
            result = operation_func(tracker, *args, **kwargs)
            tracker.complete()
            return result
        except Exception as e:
            tracker.close()
            raise e
        finally:
            tracker.close()

    return wrapper


def main():
    """Run the main Streamlit application."""
    st.set_page_config(
        page_title="SousChef - Chef to Ansible Migration",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("SousChef - Visual Migration Planning")
    st.markdown("*AI-powered Chef to Ansible migration planning interface*")

    # Sidebar navigation
    page = st.sidebar.selectbox(
        "Navigation",
        [
            "Dashboard",
            "Cookbook Analysis",
            "Migration Planning",
            "Dependency Mapping",
            "Validation Reports",
        ],
        help="Choose the section you want to work with. "
        "Use arrow keys to navigate options.",
        key="main_navigation",
    )

    # Main content area
    if page == "Dashboard":
        show_dashboard()
    elif page == "Cookbook Analysis":
        show_cookbook_analysis_page()
    elif page == "Migration Planning":
        show_migration_planning()
    elif page == "Dependency Mapping":
        show_dependency_mapping()
    elif page == "Validation Reports":
        show_validation_reports()


def show_dashboard():
    """Show the main dashboard with migration overview."""
    st.header("Migration Dashboard")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Cookbooks Analyzed", "0", "Ready to analyze")
        st.caption("Total cookbooks processed")

    with col2:
        st.metric("Migration Complexity", "Unknown", "Assessment needed")
        st.caption("Overall migration effort")

    with col3:
        st.metric("Conversion Rate", "0%", "Start migration")
        st.caption("Successful conversions")

    st.divider()

    # Quick actions
    st.subheader("Quick Actions")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Analyze Cookbook Directory", type="primary", use_container_width=True
        ):
            st.rerun()  # This will trigger navigation to cookbook analysis

    with col2:
        if st.button(
            "Generate Migration Plan", type="secondary", use_container_width=True
        ):
            st.rerun()  # This will trigger navigation to migration planning

    # Recent activity
    st.subheader("Recent Activity")
    st.info("No recent migration activity. Start by analyzing your cookbooks!")


def show_migration_planning():
    """Show migration planning interface."""
    st.header("Migration Planning")

    # Import assessment functions
    from souschef.assessment import generate_migration_plan

    # Migration planning wizard
    st.markdown("""
    Plan your Chef-to-Ansible migration with this interactive wizard.
    Get detailed timelines, effort estimates, and risk assessments.
    """)

    # Step 1: Cookbook Selection
    st.subheader("Step 1: Cookbook Selection")

    col1, col2 = st.columns([3, 1])

    with col1:
        cookbook_paths = st.text_area(
            "Cookbook Paths",
            placeholder="/path/to/cookbooks/nginx,/path/to/cookbooks/apache2,/path/to/cookbooks/mysql",
            help="Enter comma-separated paths to your Chef cookbooks",
            height=100,
        )

    with col2:
        quick_select = st.selectbox(
            "Quick Examples",
            ["", "Single Cookbook", "Multiple Cookbooks", "Full Migration"],
            help="Load example cookbook configurations",
        )

    # Load example configurations
    if quick_select == "Single Cookbook":
        cookbook_paths = "/path/to/cookbooks/nginx"
    elif quick_select == "Multiple Cookbooks":
        cookbook_paths = (
            "/path/to/cookbooks/nginx,/path/to/cookbooks/apache2,"
            "/path/to/cookbooks/mysql"
        )
    elif quick_select == "Full Migration":
        cookbook_paths = (
            "/path/to/cookbooks/nginx,/path/to/cookbooks/apache2,"
            "/path/to/cookbooks/mysql,/path/to/cookbooks/postgresql,"
            "/path/to/cookbooks/redis"
        )

    # Step 2: Migration Strategy
    st.subheader("Step 2: Migration Strategy")

    col1, col2 = st.columns(2)

    with col1:
        migration_strategy = st.selectbox(
            "Migration Approach",
            ["phased", "big_bang", "parallel"],
            help="Choose your migration strategy",
            format_func=lambda x: {
                "phased": "Phased Migration (Recommended)",
                "big_bang": "Big Bang Migration",
                "parallel": "Parallel Migration",
            }.get(x, x),
        )

    with col2:
        timeline_weeks = st.slider(
            "Timeline (Weeks)",
            min_value=4,
            max_value=24,
            value=12,
            help="Target timeline for migration completion",
        )

    # Strategy descriptions
    strategy_descriptions = {
        "phased": """
        **Phased Migration** - Migrate cookbooks in stages based on complexity
        and dependencies.
        - Lower risk with incremental progress
        - Easier rollback if issues occur
        - Longer timeline but more controlled
        - Recommended for most organizations
        """,
        "big_bang": """
        **Big Bang Migration** - Convert all cookbooks simultaneously and deploy
        at once.
        - Faster overall timeline
        - Higher risk and coordination required
        - Requires comprehensive testing
        - Best for small, well-understood environments
        """,
        "parallel": """
        **Parallel Migration** - Run Chef and Ansible side-by-side during transition.
        - Zero downtime possible
        - Most complex to manage
        - Requires dual maintenance
        - Best for critical production systems
        """,
    }

    with st.expander("Strategy Details"):
        st.markdown(strategy_descriptions.get(migration_strategy, ""))

    # Step 3: Generate Plan
    st.subheader("Step 3: Generate Migration Plan")

    if st.button("Generate Migration Plan", type="primary", use_container_width=True):
        if not cookbook_paths.strip():
            st.error("Please enter cookbook paths to generate a migration plan.")
            return

        # Create progress tracker
        progress_tracker = ProgressTracker(
            total_steps=7, description="Generating migration plan..."
        )

        try:
            progress_tracker.update(1, "Scanning cookbook directories...")

            # Generate migration plan
            plan_result = generate_migration_plan(
                cookbook_paths.strip(), migration_strategy, timeline_weeks
            )

            progress_tracker.update(2, "Analyzing cookbook complexity...")
            progress_tracker.update(3, "Assessing migration risks...")
            progress_tracker.update(4, "Calculating resource requirements...")
            progress_tracker.update(5, "Generating timeline estimates...")
            progress_tracker.update(6, "Creating migration phases...")

            # Store results in session state for persistence
            st.session_state.migration_plan = plan_result
            st.session_state.cookbook_paths = cookbook_paths.strip()
            st.session_state.strategy = migration_strategy
            st.session_state.timeline = timeline_weeks

            progress_tracker.complete("Migration plan generated!")
            st.success("Migration plan generated successfully!")
            st.rerun()

        except Exception as e:
            progress_tracker.close()
            st.error(f"Error generating migration plan: {e}")
            return

    # Display results if available
    if "migration_plan" in st.session_state:
        display_migration_plan_results()


def _display_migration_summary_metrics(cookbook_paths, strategy, timeline):
    """Display migration overview summary metrics."""
    st.subheader("Migration Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        cookbook_count = len(cookbook_paths.split(","))
        st.metric("Cookbooks", cookbook_count)

    with col2:
        st.metric("Strategy", strategy.replace("_", " ").title())

    with col3:
        st.metric("Timeline", f"{timeline} weeks")

    with col4:
        st.metric("Status", "Plan Generated")


def _display_migration_plan_details(plan_result):
    """Display the detailed migration plan sections."""
    st.subheader("Migration Plan Details")

    # Split the plan into sections and display
    plan_sections = plan_result.split("\n## ")

    for section in plan_sections:
        if section.strip():
            if not section.startswith("#"):
                section = "## " + section

            # Clean up section headers
            section = section.replace("## Executive Summary", "### Executive Summary")
            section = section.replace("## Migration Phases", "### Migration Phases")
            section = section.replace("## Timeline", "### Timeline")
            section = section.replace("## Team Requirements", "### Team Requirements")

            st.markdown(section)


def _display_migration_action_buttons(cookbook_paths):
    """Display action buttons for next steps."""
    st.subheader("Next Steps")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📊 Generate Detailed Report", use_container_width=True):
            with st.spinner("Generating detailed migration report..."):
                try:
                    from souschef.assessment import generate_migration_report

                    report = generate_migration_report(
                        "assessment_complete", "executive", "yes"
                    )
                    st.session_state.detailed_report = report
                    st.success("Detailed report generated!")
                except Exception as e:
                    st.error(f"Error generating report: {e}")

    with col2:
        if st.button("🔍 Analyze Dependencies", use_container_width=True):
            if len(cookbook_paths.split(",")) == 1:
                # Single cookbook dependency analysis
                cookbook_path = cookbook_paths.split(",")[0].strip()
                with st.spinner(f"Analyzing dependencies for {cookbook_path}..."):
                    try:
                        from souschef.assessment import analyze_cookbook_dependencies

                        dep_analysis = analyze_cookbook_dependencies(cookbook_path)
                        st.session_state.dep_analysis = dep_analysis
                        st.success("Dependency analysis complete!")
                    except Exception as e:
                        st.error(f"Error analyzing dependencies: {e}")
            else:
                st.info(
                    "Dependency analysis is optimized for single cookbooks. "
                    "Select one cookbook path for detailed analysis."
                )

    with col3:
        if st.button("📥 Export Plan", use_container_width=True):
            # Create downloadable plan
            plan_content = f"""# Chef to Ansible Migration Plan
Generated: {st.session_state.get("timestamp", "Unknown")}

## Configuration
- Cookbook Paths: {cookbook_paths}
- Strategy: {st.session_state.strategy}
- Timeline: {st.session_state.timeline} weeks

## Migration Plan
{st.session_state.migration_plan}
"""

            st.download_button(
                label="Download Migration Plan",
                data=plan_content,
                file_name="migration_plan.md",
                mime="text/markdown",
                help="Download the complete migration plan as Markdown",
            )


def _display_additional_reports():
    """Display detailed report and dependency analysis if available."""
    # Display detailed report if generated
    if "detailed_report" in st.session_state:
        with st.expander("📊 Detailed Migration Report"):
            st.markdown(st.session_state.detailed_report)

    # Display dependency analysis if generated
    if "dep_analysis" in st.session_state:
        with st.expander("🔍 Dependency Analysis"):
            st.markdown(st.session_state.dep_analysis)


def display_migration_plan_results():
    """Display the generated migration plan results."""
    plan_result = st.session_state.migration_plan
    cookbook_paths = st.session_state.cookbook_paths
    strategy = st.session_state.strategy
    timeline = st.session_state.timeline

    _display_migration_summary_metrics(cookbook_paths, strategy, timeline)
    _display_migration_plan_details(plan_result)
    _display_migration_action_buttons(cookbook_paths)
    _display_additional_reports()


def show_dependency_mapping():
    """Show dependency mapping visualization."""
    st.header("Dependency Mapping")

    # Import assessment functions
    from souschef.assessment import analyze_cookbook_dependencies

    st.markdown("""
    Visualize and analyze cookbook dependencies to understand migration order
    and identify potential circular dependencies.
    """)

    # Cookbook path input
    cookbook_path = st.text_input(
        "Cookbook Directory Path",
        placeholder="/path/to/your/cookbooks",
        help="Enter the path to your cookbooks directory for dependency analysis",
    )

    # Analysis options
    col1, col2 = st.columns(2)

    with col1:
        dependency_depth = st.selectbox(
            "Analysis Depth",
            ["direct", "transitive", "full"],
            help="How deep to analyze dependencies",
            format_func=lambda x: {
                "direct": "Direct Dependencies Only",
                "transitive": "Include Transitive Dependencies",
                "full": "Full Dependency Graph",
            }.get(x, x),
        )

    with col2:
        visualization_type = st.selectbox(
            "Visualization",
            ["text", "graph", "interactive"],
            help="How to display dependency information",
            format_func=lambda x: {
                "text": "Text Summary",
                "graph": "Static Graph View",
                "interactive": "Interactive Graph",
            }.get(x, x),
        )

    # Analysis button
    if st.button("Analyze Dependencies", type="primary", use_container_width=True):
        if not cookbook_path.strip():
            st.error("Please enter a cookbook directory path.")
            return

        # Create progress tracker
        progress_tracker = ProgressTracker(
            total_steps=5, description="Analyzing cookbook dependencies..."
        )

        try:
            progress_tracker.update(1, "Scanning cookbook directory...")

            # Analyze dependencies
            analysis_result = analyze_cookbook_dependencies(
                cookbook_path.strip(), dependency_depth
            )

            progress_tracker.update(2, "Parsing dependency relationships...")
            progress_tracker.update(3, "Detecting circular dependencies...")
            progress_tracker.update(4, "Generating migration recommendations...")

            # Store results
            st.session_state.dep_analysis_result = analysis_result
            st.session_state.dep_cookbook_path = cookbook_path.strip()
            st.session_state.dep_depth = dependency_depth
            st.session_state.dep_viz_type = visualization_type

            progress_tracker.complete("Dependency analysis completed!")
            st.success("Analysis completed successfully!")
            st.rerun()

        except Exception as e:
            progress_tracker.close()
            st.error(f"Error analyzing dependencies: {e}")
            return

    # Display results if available
    if "dep_analysis_result" in st.session_state:
        display_dependency_analysis_results()


def _extract_dependency_relationships(lines):
    """Extract dependency relationships from analysis lines."""
    dependencies = {}
    current_section = None

    for line in lines:
        line = line.strip()
        if "Direct Dependencies:" in line:
            current_section = "direct"
        elif "Transitive Dependencies:" in line:
            current_section = "transitive"
        elif line.startswith("- ") and current_section in ["direct", "transitive"]:
            # Regular dependencies
            dep_text = line[2:].strip()
            if ":" in dep_text:
                parts = dep_text.split(":", 1)
                cookbook = parts[0].strip()
                deps = parts[1].strip()
                if deps and deps != "None":
                    dep_list = [d.strip() for d in deps.split(",")]
                    dependencies[cookbook] = dep_list

    return dependencies


def _extract_circular_and_community_deps(lines):
    """Extract circular dependencies and community cookbooks."""
    circular_deps = []
    community_cookbooks = []
    current_section = None

    for line in lines:
        line = line.strip()
        if "Circular Dependencies:" in line:
            current_section = "circular"
        elif "Community Cookbooks:" in line:
            current_section = "community"
        elif line.startswith("- ") and current_section:
            if current_section == "circular":
                # Parse circular dependency pairs
                dep_text = line[2:].strip()
                if "->" in dep_text:
                    parts = dep_text.split("->")
                    if len(parts) >= 2:
                        circular_deps.append((parts[0].strip(), parts[1].strip()))
            elif current_section == "community":
                # Community cookbooks
                cookbook = line[2:].strip()
                if cookbook:
                    community_cookbooks.append(cookbook)

    return circular_deps, community_cookbooks


def _parse_dependency_analysis(analysis_result):
    """Parse dependency analysis result into structured data."""
    lines = analysis_result.split("\n")

    dependencies = _extract_dependency_relationships(lines)
    circular_deps, community_cookbooks = _extract_circular_and_community_deps(lines)

    return dependencies, circular_deps, community_cookbooks


def _create_networkx_graph(dependencies, circular_deps, community_cookbooks):
    """Create NetworkX graph from dependency data."""
    import networkx as nx

    graph = nx.DiGraph()

    # Add nodes and edges
    for cookbook, deps in dependencies.items():
        graph.add_node(cookbook, node_type="cookbook")
        for dep in deps:
            graph.add_node(dep, node_type="dependency")
            graph.add_edge(cookbook, dep)

    # Add circular dependency edges with different styling
    for source, target in circular_deps:
        graph.add_edge(source, target, circular=True)

    # Mark community cookbooks
    for cookbook in community_cookbooks:
        if cookbook in graph.nodes:
            graph.nodes[cookbook]["community"] = True

    return graph


def _calculate_graph_positions(graph, layout_algorithm):
    """Calculate node positions using specified layout algorithm."""
    import networkx as nx

    # Choose layout algorithm based on graph size and user preference
    num_nodes = len(graph.nodes)
    if layout_algorithm == "auto":
        if num_nodes < 10:
            layout_algorithm = "spring"
        elif num_nodes < 50:
            layout_algorithm = "kamada_kawai"
        else:
            layout_algorithm = "circular"

    # Calculate positions using selected layout algorithm
    if layout_algorithm == "spring":
        pos = nx.spring_layout(graph, k=2, iterations=50, seed=42)
    elif layout_algorithm == "circular":
        pos = nx.circular_layout(graph)
    elif layout_algorithm == "kamada_kawai":
        try:
            pos = nx.kamada_kawai_layout(graph, seed=42)
        except Exception:
            # Fallback to spring layout if kamada_kawai fails
            pos = nx.spring_layout(graph, k=2, iterations=50, seed=42)
    else:
        pos = nx.spring_layout(graph, k=2, iterations=50, seed=42)

    return pos, layout_algorithm


def _create_plotly_edge_traces(graph, pos):
    """Create edge traces for Plotly graph."""
    import plotly.graph_objects as go

    edge_traces = []

    # Regular edges
    edge_x = []
    edge_y = []
    for edge in graph.edges():
        if not graph.edges[edge].get("circular", False):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

    if edge_x:
        edge_traces.append(
            go.Scatter(
                x=edge_x,
                y=edge_y,
                line={"width": 2, "color": "#888"},
                hoverinfo="none",
                mode="lines",
                name="Dependencies",
            )
        )

    # Circular dependency edges (red)
    circ_edge_x = []
    circ_edge_y = []
    for edge in graph.edges():
        if graph.edges[edge].get("circular", False):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            circ_edge_x.extend([x0, x1, None])
            circ_edge_y.extend([y0, y1, None])

    if circ_edge_x:
        edge_traces.append(
            go.Scatter(
                x=circ_edge_x,
                y=circ_edge_y,
                line={"width": 3, "color": "red"},
                hoverinfo="none",
                mode="lines",
                name="Circular Dependencies",
            )
        )

    return edge_traces


def _create_plotly_node_trace(graph, pos):
    """Create node trace for Plotly graph."""
    import plotly.graph_objects as go

    node_x = []
    node_y = []
    node_text = []
    node_colors = []
    node_sizes = []

    for node in graph.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)

        # Dynamic node sizing based on connectivity
        degree = graph.degree(node)
        node_sizes.append(max(15, min(30, 15 + degree * 2)))

        # Color coding
        if graph.nodes[node].get("community", False):
            node_colors.append("lightgreen")  # Community cookbooks
        elif any(
            graph.edges[edge].get("circular", False)
            for edge in graph.in_edges(node)
            if edge[1] == node
        ):
            node_colors.append("red")  # Involved in circular deps
        elif graph.in_degree(node) > 0:
            node_colors.append("lightblue")  # Has dependencies
        else:
            node_colors.append("lightgray")  # Leaf dependencies

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        hoverinfo="text",
        text=node_text,
        textposition="top center",
        marker={
            "size": node_sizes,
            "color": node_colors,
            "line_width": 2,
            "line_color": "darkgray",
        },
        name="Cookbooks",
    )

    return node_trace


def _create_plotly_figure_layout(num_nodes, layout_algorithm):
    """Create Plotly figure layout."""
    import plotly.graph_objects as go

    return go.Layout(
        title=f"Cookbook Dependency Graph ({num_nodes} nodes, "
        f"{layout_algorithm} layout)",
        titlefont_size=16,
        showlegend=True,
        hovermode="closest",
        margin={"b": 20, "l": 5, "r": 5, "t": 40},
        xaxis={
            "showgrid": False,
            "zeroline": False,
            "showticklabels": False,
        },
        yaxis={
            "showgrid": False,
            "zeroline": False,
            "showticklabels": False,
        },
        plot_bgcolor="white",
    )


def _create_interactive_plotly_graph(graph, pos, num_nodes, layout_algorithm):
    """Create interactive Plotly graph visualization."""
    import plotly.graph_objects as go

    edge_traces = _create_plotly_edge_traces(graph, pos)
    node_trace = _create_plotly_node_trace(graph, pos)
    layout = _create_plotly_figure_layout(num_nodes, layout_algorithm)

    # Create the figure
    fig = go.Figure(data=edge_traces + [node_trace], layout=layout)

    return fig


def _create_static_matplotlib_graph(graph, pos, num_nodes, layout_algorithm):
    """Create static matplotlib graph visualization."""
    import matplotlib.pyplot as plt

    plt.figure(figsize=(12, 8))

    # Draw regular edges
    regular_edges = [
        (u, v) for u, v, d in graph.edges(data=True) if not d.get("circular", False)
    ]
    if regular_edges:
        import networkx as nx

        nx.draw_networkx_edges(
            graph,
            pos,
            edgelist=regular_edges,
            edge_color="gray",
            arrows=True,
            arrowsize=20,
            width=2,
            alpha=0.7,
        )

    # Draw circular dependency edges
    circular_edges = [
        (u, v) for u, v, d in graph.edges(data=True) if d.get("circular", False)
    ]
    if circular_edges:
        import networkx as nx

        nx.draw_networkx_edges(
            graph,
            pos,
            edgelist=circular_edges,
            edge_color="red",
            arrows=True,
            arrowsize=25,
            width=3,
            alpha=0.9,
            style="dashed",
        )

    # Color nodes
    node_colors = []
    for node in graph.nodes():
        if graph.nodes[node].get("community", False):
            node_colors.append("lightgreen")  # Community cookbooks
        elif any(
            graph.edges[edge].get("circular", False)
            for edge in graph.in_edges(node)
            if edge[1] == node
        ):
            node_colors.append("red")  # Involved in circular deps
        elif graph.in_degree(node) > 0:
            node_colors.append("lightblue")  # Has dependencies
        else:
            node_colors.append("lightgray")  # Leaf dependencies

    # Draw nodes with size based on connectivity
    node_sizes = [
        max(300, min(1200, 300 + graph.degree(node) * 100)) for node in graph.nodes()
    ]

    # Draw nodes
    import networkx as nx

    nx.draw_networkx_nodes(
        graph,
        pos,
        node_color=node_colors,
        node_size=node_sizes,
        alpha=0.8,
        linewidths=2,
        edgecolors="darkgray",
    )

    # Draw labels
    nx.draw_networkx_labels(graph, pos, font_size=8, font_weight="bold")

    plt.title(
        f"Cookbook Dependency Graph ({num_nodes} nodes, {layout_algorithm} layout)",
        fontsize=16,
        pad=20,
    )
    plt.axis("off")
    plt.tight_layout()

    return plt.gcf()


def create_dependency_graph(analysis_result, viz_type, layout_algorithm="auto"):
    """
    Create a dependency graph visualization.

    Args:
        analysis_result: Text analysis result from dependency analysis
        viz_type: Visualization type ("interactive" or "static")
        layout_algorithm: Layout algorithm to use ("auto", "spring",
                          "circular", "kamada_kawai")

    Returns:
        Plotly figure for interactive graphs, matplotlib figure for static graphs

    """
    try:
        # Parse the analysis result to extract dependencies
        dependencies, circular_deps, community_cookbooks = _parse_dependency_analysis(
            analysis_result
        )

        # Create NetworkX graph
        graph = _create_networkx_graph(dependencies, circular_deps, community_cookbooks)

        if len(graph.nodes) == 0:
            return None

        # Calculate positions
        pos, final_layout = _calculate_graph_positions(graph, layout_algorithm)

        if viz_type == "interactive":
            return _create_interactive_plotly_graph(
                graph, pos, len(graph.nodes), final_layout
            )
        else:
            return _create_static_matplotlib_graph(
                graph, pos, len(graph.nodes), final_layout
            )

    except Exception as e:
        st.error(f"Error creating dependency graph: {e}")
        return None


def _parse_dependency_metrics_from_result(analysis_result):
    """Parse dependency analysis result to extract key metrics."""
    lines = analysis_result.split("\n")

    # Extract key metrics from the analysis
    direct_deps = 0
    transitive_deps = 0
    circular_deps = 0
    community_cookbooks = 0

    for line in lines:
        if "Direct Dependencies:" in line:
            with contextlib.suppress(ValueError):
                direct_deps = int(line.split(":")[1].strip())
        elif "Transitive Dependencies:" in line:
            with contextlib.suppress(ValueError):
                transitive_deps = int(line.split(":")[1].strip())
        elif "Circular Dependencies:" in line:
            with contextlib.suppress(ValueError):
                circular_deps = int(line.split(":")[1].strip())
        elif "Community Cookbooks:" in line:
            with contextlib.suppress(ValueError):
                community_cookbooks = int(line.split(":")[1].strip())

    return direct_deps, transitive_deps, circular_deps, community_cookbooks


def _display_dependency_summary_metrics(
    direct_deps, transitive_deps, circular_deps, community_cookbooks
):
    """Display dependency analysis summary metrics."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Direct Dependencies", direct_deps)

    with col2:
        st.metric("Transitive Dependencies", transitive_deps)

    with col3:
        st.metric(
            "Circular Dependencies",
            circular_deps,
            delta="⚠️ Check" if circular_deps > 0 else "✅ OK",
        )

    with col4:
        st.metric("Community Cookbooks", community_cookbooks)


def _display_dependency_graph_visualization(analysis_result, viz_type, selected_layout):
    """Display the dependency graph visualization section."""
    try:
        # Create cache key for graph data
        cache_key = f"graph_{hash(analysis_result)}_{viz_type}_{selected_layout}"

        # Check if we have cached graph data
        if cache_key in st.session_state and st.session_state.get(
            "graph_cache_enabled", True
        ):
            graph_data = st.session_state[cache_key]
            st.info("📋 Using cached graph data")
        else:
            # Create dependency graph
            graph_data = create_dependency_graph(
                analysis_result, viz_type, selected_layout
            )

            # Cache the result
            if graph_data is not None and st.session_state.get(
                "graph_cache_enabled", True
            ):
                st.session_state[cache_key] = graph_data

        # Cache control
        with st.expander("⚙️ Graph Settings"):
            cache_enabled = st.checkbox(
                "Enable Graph Caching",
                value=st.session_state.get("graph_cache_enabled", True),
                help="Cache graph data to improve performance for repeated views",
            )
            st.session_state["graph_cache_enabled"] = cache_enabled

            if st.button(
                "🗑️ Clear Graph Cache", help="Clear cached graph data to free memory"
            ):
                # Clear all cached graphs
                keys_to_remove = [k for k in st.session_state if k.startswith("graph_")]
                for key in keys_to_remove:
                    del st.session_state[key]
                st.success("Graph cache cleared!")
                st.rerun()

        if graph_data:
            _display_graph_with_export_options(graph_data, viz_type)
        else:
            st.info("No dependency relationships found to visualize.")

    except Exception as e:
        _handle_graph_visualization_error(e, analysis_result)


def _display_graph_with_export_options(graph_data, viz_type):
    """Display graph and provide export options."""
    if viz_type == "interactive":
        # Interactive Plotly graph
        st.plotly_chart(graph_data, use_container_width=True)

        # Export options for interactive graph
        st.subheader("Export Graph")
        col1, col2, col3 = st.columns(3)

        with col1:
            # Export as HTML
            html_content = graph_data.to_html(full_html=False, include_plotlyjs="cdn")
            st.download_button(
                label="📄 Export as HTML",
                data=html_content,
                file_name="dependency_graph.html",
                mime="text/html",
                help="Download interactive graph as HTML file",
            )

        with col2:
            # Export as JSON
            json_data = graph_data.to_json()
            st.download_button(
                label="📊 Export as JSON",
                data=json_data,
                file_name="dependency_graph.json",
                mime="application/json",
                help="Download graph data as JSON",
            )

        with col3:
            # Export as PNG (requires kaleido)
            try:
                import plotly.io as pio

                png_data = pio.to_image(graph_data, format="png")
                st.download_button(
                    label="🖼️ Export as PNG",
                    data=png_data,
                    file_name="dependency_graph.png",
                    mime="image/png",
                    help="Download graph as PNG image",
                )
            except ImportError:
                st.info("PNG export requires additional dependencies")

    else:
        # Static matplotlib graph
        st.pyplot(graph_data)

        # Export options for static graph
        st.subheader("Export Graph")
        col1, col2 = st.columns(2)

        with col1:
            # Export as PNG
            import io

            buf = io.BytesIO()
            graph_data.savefig(buf, format="png", dpi=300, bbox_inches="tight")
            buf.seek(0)
            st.download_button(
                label="🖼️ Export as PNG",
                data=buf.getvalue(),
                file_name="dependency_graph.png",
                mime="image/png",
                help="Download graph as high-resolution PNG",
            )

        with col2:
            # Export as SVG
            buf_svg = io.BytesIO()
            graph_data.savefig(buf_svg, format="svg", bbox_inches="tight")
            buf_svg.seek(0)
            st.download_button(
                label="📈 Export as SVG",
                data=buf_svg.getvalue(),
                file_name="dependency_graph.svg",
                mime="image/svg+xml",
                help="Download graph as scalable SVG",
            )


def _handle_graph_visualization_error(error, analysis_result):
    """Handle graph visualization errors with fallback display."""
    st.error("❌ **Graph Visualization Error**")
    with st.expander("Error Details"):
        st.code(str(error), language="text")
        st.markdown("""
        **Possible causes:**
        - Invalid dependency analysis data
        - Graph layout algorithm failed for this data
        - Memory constraints for large graphs

        **Suggestions:**
        - Try a different layout algorithm
        - Reduce the scope of your dependency analysis
        - Check the dependency analysis output for issues
        """)

    # Fallback: show text summary
    st.info("📄 Showing text-based dependency summary instead:")
    st.text_area(
        "Dependency Analysis Text",
        analysis_result,
        height=300,
        help="Raw dependency analysis output",
    )


def _display_dependency_analysis_sections(analysis_result):
    """Display dependency analysis results in expandable sections."""
    # Split analysis into sections
    sections = analysis_result.split("\n## ")

    for section in sections:
        if section.strip():
            if not section.startswith("#"):
                section = "## " + section

            # Add expanders for different sections
            if "Migration Order Recommendations" in section:
                with st.expander("📋 Migration Order Recommendations"):
                    st.markdown(
                        section.replace("## Migration Order Recommendations", "")
                    )
            elif "Dependency Graph" in section:
                with st.expander("🔗 Dependency Graph"):
                    st.markdown(section.replace("## Dependency Graph", ""))
            elif "Circular Dependencies" in section:
                with st.expander("⚠️ Circular Dependencies"):
                    st.markdown(section.replace("## Circular Dependencies", ""))
            elif "Community Cookbooks" in section:
                with st.expander("🌐 Community Cookbooks"):
                    st.markdown(section.replace("## Community Cookbooks", ""))
            elif "Migration Impact Analysis" in section:
                with st.expander("📊 Migration Impact Analysis"):
                    st.markdown(section.replace("## Migration Impact Analysis", ""))
            else:
                st.markdown(section)


def _display_migration_recommendations(circular_deps, community_cookbooks, direct_deps):
    """Display migration recommendations based on analysis results."""
    st.subheader("Migration Recommendations")

    if circular_deps > 0:
        st.error(
            "⚠️ **Critical Issue**: Circular dependencies detected. "
            "Resolve before migration."
        )
        st.markdown("""
        **Resolution Steps:**
        1. Review the circular dependency pairs
        2. Refactor cookbooks to break circular references
        3. Consider combining tightly coupled cookbooks
        4. Update dependency declarations
        """)

    if community_cookbooks > 0:
        st.success(
            f"✅ **Good News**: {community_cookbooks} community cookbooks identified."
        )
        st.markdown("""
        **Recommendations:**
        - Replace with Ansible Galaxy roles where possible
        - Review community cookbook versions and security
        - Consider forking and maintaining custom versions if needed
        """)

    if direct_deps > 10:
        st.warning("⚠️ **Complex Dependencies**: High dependency count detected.")
        st.markdown("""
        **Consider:**
        - Breaking down monolithic cookbooks
        - Implementing proper dependency injection
        - Planning migration in smaller phases
        """)


def _display_dependency_export_options(
    analysis_result,
    cookbook_path,
    depth,
    direct_deps,
    transitive_deps,
    circular_deps,
    community_cookbooks,
):
    """Display export options for dependency analysis."""
    st.subheader("Export Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="📥 Download Full Analysis",
            data=analysis_result,
            file_name="dependency_analysis.md",
            mime="text/markdown",
            help="Download complete dependency analysis",
        )

    with col2:
        # Create a simplified JSON export
        analysis_json = {
            "cookbook_path": cookbook_path,
            "analysis_depth": depth,
            "metrics": {
                "direct_dependencies": direct_deps,
                "transitive_dependencies": transitive_deps,
                "circular_dependencies": circular_deps,
                "community_cookbooks": community_cookbooks,
            },
            "full_analysis": analysis_result,
        }

        import json

        st.download_button(
            label="📊 Download JSON Summary",
            data=json.dumps(analysis_json, indent=2),
            file_name="dependency_analysis.json",
            mime="application/json",
            help="Download analysis summary as JSON",
        )


def display_dependency_analysis_results():
    """Display dependency analysis results."""
    analysis_result = st.session_state.dep_analysis_result
    cookbook_path = st.session_state.dep_cookbook_path
    depth = st.session_state.dep_depth
    viz_type = st.session_state.get("dep_viz_type", "text")

    # Summary metrics
    st.subheader("Dependency Analysis Summary")

    # Parse metrics from analysis result
    direct_deps, transitive_deps, circular_deps, community_cookbooks = (
        _parse_dependency_metrics_from_result(analysis_result)
    )

    # Display summary metrics
    _display_dependency_summary_metrics(
        direct_deps, transitive_deps, circular_deps, community_cookbooks
    )

    # Analysis depth indicator
    st.info(f"Analysis performed with **{depth}** depth on: `{cookbook_path}`")

    # Graph Visualization Section
    if viz_type in ["graph", "interactive"]:
        st.subheader("📊 Dependency Graph Visualization")

        # Layout algorithm selector
        layout_options = ["auto", "spring", "circular", "kamada_kawai"]
        selected_layout = st.selectbox(
            "Layout Algorithm",
            layout_options,
            help="Choose graph layout algorithm. 'auto' selects best "
            "algorithm based on graph size.",
            format_func=lambda x: {
                "auto": "Auto (recommended)",
                "spring": "Spring Layout",
                "circular": "Circular Layout",
                "kamada_kawai": "Kamada-Kawai Layout",
            }.get(x, x),
        )

        _display_dependency_graph_visualization(
            analysis_result, viz_type, selected_layout
        )

    # Display analysis results
    st.subheader("Dependency Analysis Details")

    _display_dependency_analysis_sections(analysis_result)

    # Migration recommendations
    _display_migration_recommendations(circular_deps, community_cookbooks, direct_deps)

    # Export options
    _display_dependency_export_options(
        analysis_result,
        cookbook_path,
        depth,
        direct_deps,
        transitive_deps,
        circular_deps,
        community_cookbooks,
    )


def show_validation_reports():
    """Show validation reports and conversion validation."""
    st.header("Validation Reports")

    # Import validation functions
    from souschef.core.validation import ValidationEngine

    st.markdown("""
    Validate Chef to Ansible conversions and generate comprehensive
    validation reports for migration quality assurance.
    """)

    # Validation options
    col1, col2 = st.columns(2)

    with col1:
        validation_type = st.selectbox(
            "Validation Type",
            ["syntax", "logic", "security", "performance", "full"],
            help="Type of validation to perform",
            format_func=lambda x: {
                "syntax": "Syntax Validation",
                "logic": "Logic & Structure Validation",
                "security": "Security Best Practices",
                "performance": "Performance Analysis",
                "full": "Complete Validation Suite",
            }.get(x, x),
        )

    with col2:
        output_format = st.selectbox(
            "Output Format",
            ["text", "json", "html"],
            help="Format for validation reports",
            format_func=lambda x: {
                "text": "Text Report",
                "json": "JSON Data",
                "html": "HTML Report",
            }.get(x, x),
        )

    # File/Directory input
    st.subheader("Input Source")

    input_type = st.radio(
        "Input Type",
        ["Directory", "Single File"],
        horizontal=True,
        help="Validate a directory of files or a single file",
    )

    if input_type == "Directory":
        input_path = st.text_input(
            "Directory Path",
            placeholder="/path/to/ansible/playbooks",
            help="Path to directory containing Ansible playbooks to validate",
        )
    else:
        input_path = st.text_input(
            "File Path",
            placeholder="/path/to/playbook.yml",
            help="Path to single Ansible playbook file to validate",
        )

    # Validation options
    st.subheader("Validation Options")

    col1, col2, col3 = st.columns(3)

    with col1:
        strict_mode = st.checkbox(
            "Strict Mode", help="Fail on warnings, not just errors"
        )

    with col2:
        include_best_practices = st.checkbox(
            "Include Best Practices",
            value=True,
            help="Check for Ansible best practices",
        )

    with col3:
        generate_recommendations = st.checkbox(
            "Generate Recommendations",
            value=True,
            help="Provide improvement suggestions",
        )

    # Validation button
    if st.button("Run Validation", type="primary", use_container_width=True):
        if not input_path.strip():
            st.error("Please enter a path to validate.")
            return

        # Create progress tracker
        progress_tracker = ProgressTracker(
            total_steps=6, description="Running validation..."
        )

        try:
            progress_tracker.update(1, "Preparing validation environment...")

            # Prepare validation options
            options = {
                "strict": strict_mode,
                "best_practices": include_best_practices,
                "recommendations": generate_recommendations,
                "format": output_format,
            }

            progress_tracker.update(2, "Scanning input files...")
            progress_tracker.update(3, "Running syntax validation...")
            progress_tracker.update(4, "Performing logic checks...")

            # Run validation
            engine = ValidationEngine()
            validation_results = engine.validate_conversion(
                validation_type, input_path.strip()
            )

            # Format the results as text
            validation_result = "\n".join(
                [
                    f"{result.level.value.upper()}: {result.message}"
                    for result in validation_results
                ]
            )

            progress_tracker.update(5, "Generating validation report...")

            # Store results
            st.session_state.validation_result = validation_result
            st.session_state.validation_path = input_path.strip()
            st.session_state.validation_type = validation_type
            st.session_state.validation_options = options

            progress_tracker.complete("Validation completed!")
            st.success("Validation completed successfully!")
            st.rerun()

        except Exception as e:
            progress_tracker.close()
            st.error(f"Error during validation: {e}")
            return

    # Display results if available
    if "validation_result" in st.session_state:
        display_validation_results()


def _parse_validation_metrics(validation_result):
    """Parse validation result to extract key metrics."""
    lines = validation_result.split("\n")

    errors = 0
    warnings = 0
    passed = 0
    total_checks = 0

    for line in lines:
        if "ERROR:" in line.upper():
            errors += 1
        elif "WARNING:" in line.upper():
            warnings += 1
        elif "PASSED:" in line.upper() or "✓" in line:
            passed += 1
        if "Total checks:" in line.lower():
            with contextlib.suppress(ValueError):
                total_checks = int(line.split(":")[1].strip())

    return errors, warnings, passed, total_checks


def _display_validation_summary_metrics(errors, warnings, passed, total_checks):
    """Display validation summary metrics."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Checks", total_checks)

    with col2:
        st.metric("Passed", passed, delta="✅" if passed > 0 else "")

    with col3:
        st.metric("Warnings", warnings, delta="⚠️" if warnings > 0 else "")

    with col4:
        st.metric("Errors", errors, delta="❌" if errors > 0 else "")


def _display_validation_status(errors, warnings):
    """Display overall validation status."""
    if errors > 0:
        st.error("❌ **Validation Failed**: Critical issues found that need attention.")
    elif warnings > 0:
        st.warning(
            "⚠️ **Validation Passed with Warnings**: Review warnings before proceeding."
        )
    else:
        st.success("✅ **Validation Passed**: All checks successful!")


def _display_validation_sections(validation_result):
    """Display validation results in expandable sections."""
    # Split results into sections
    sections = validation_result.split("\n## ")

    for section in sections:
        if section.strip():
            if not section.startswith("#"):
                section = "## " + section

            # Add expanders for different sections
            if "Syntax Validation" in section:
                with st.expander("🔍 Syntax Validation"):
                    st.markdown(section.replace("## Syntax Validation", ""))
            elif "Logic Validation" in section:
                with st.expander("🧠 Logic Validation"):
                    st.markdown(section.replace("## Logic Validation", ""))
            elif "Security Validation" in section:
                with st.expander("🔒 Security Validation"):
                    st.markdown(section.replace("## Security Validation", ""))
            elif "Performance Validation" in section:
                with st.expander("⚡ Performance Validation"):
                    st.markdown(section.replace("## Performance Validation", ""))
            elif "Best Practices" in section:
                with st.expander("📋 Best Practices"):
                    st.markdown(section.replace("## Best Practices", ""))
            elif "Recommendations" in section:
                with st.expander("💡 Recommendations"):
                    st.markdown(section.replace("## Recommendations", ""))
            else:
                st.markdown(section)


def _display_validation_action_items(errors, warnings):
    """Display action items based on validation results."""
    if errors > 0 or warnings > 0:
        st.subheader("Action Items")

        if errors > 0:
            st.error("**Critical Issues to Fix:**")
            st.markdown("""
            - Review error messages above
            - Fix syntax and logic errors
            - Re-run validation after fixes
            - Consider impact on migration timeline
            """)

        if warnings > 0:
            st.warning("**Warnings to Review:**")
            st.markdown("""
            - Address security warnings
            - Review performance suggestions
            - Consider best practice recommendations
            - Document any intentional deviations
            """)


def _display_validation_export_options(
    validation_result,
    input_path,
    validation_type,
    options,
    errors,
    warnings,
    passed,
    total_checks,
):
    """Display export options for validation results."""
    st.subheader("Export Report")

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="📥 Download Full Report",
            data=validation_result,
            file_name="validation_report.md",
            mime="text/markdown",
            help="Download complete validation report",
        )

    with col2:
        # Create JSON summary
        report_json = {
            "input_path": input_path,
            "validation_type": validation_type,
            "options": options,
            "metrics": {
                "total_checks": total_checks,
                "passed": passed,
                "warnings": warnings,
                "errors": errors,
            },
            "status": "failed"
            if errors > 0
            else "warning"
            if warnings > 0
            else "passed",
            "full_report": validation_result,
        }

        import json

        st.download_button(
            label="📊 Download JSON Summary",
            data=json.dumps(report_json, indent=2),
            file_name="validation_report.json",
            mime="application/json",
            help="Download validation summary as JSON",
        )


def display_validation_results():
    """Display validation results."""
    validation_result = st.session_state.validation_result
    input_path = st.session_state.validation_path
    validation_type = st.session_state.validation_type
    options = st.session_state.validation_options

    # Summary metrics
    st.subheader("Validation Summary")

    # Parse validation result for metrics
    errors, warnings, passed, total_checks = _parse_validation_metrics(
        validation_result
    )

    # Display summary metrics
    _display_validation_summary_metrics(errors, warnings, passed, total_checks)

    # Overall status
    _display_validation_status(errors, warnings)

    # Validation details
    st.info(f"Validation type: **{validation_type}** | Path: `{input_path}`")

    # Display validation results
    st.subheader("Validation Details")

    _display_validation_sections(validation_result)

    # Action items
    _display_validation_action_items(errors, warnings)

    # Export options
    _display_validation_export_options(
        validation_result,
        input_path,
        validation_type,
        options,
        errors,
        warnings,
        passed,
        total_checks,
    )


if __name__ == "__main__":
    main()
