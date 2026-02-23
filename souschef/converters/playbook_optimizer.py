"""Playbook optimization including task deduplication and consolidation."""

from typing import Any


def detect_duplicate_tasks(tasks: list[dict[str, Any]]) -> list[tuple[int, int]]:
    """
    Detect duplicate or similar tasks in a playbook.

    Args:
        tasks: List of task dictionaries.

    Returns:
        List of (index1, index2) tuples for duplicate tasks.

    """
    duplicates: list[tuple[int, int]] = []

    for i, task1 in enumerate(tasks):
        for j, task2 in enumerate(tasks[i + 1 :], start=i + 1):
            if _tasks_are_equivalent(task1, task2):
                duplicates.append((i, j))

    return duplicates


def _tasks_are_equivalent(task1: dict[str, Any], task2: dict[str, Any]) -> bool:
    """
    Check if two tasks are equivalent (same module and parameters).

    Args:
        task1: First task dictionary.
        task2: Second task dictionary.

    Returns:
        True if tasks are equivalent, False otherwise.

    """
    # Get module names
    module1 = _extract_module_name(task1)
    module2 = _extract_module_name(task2)

    if module1 != module2:
        return False

    # Compare parameters (ignore name, register, tags)
    params1 = {
        k: v
        for k, v in task1.items()
        if k not in {"name", "register", "tags", "when", "become", "become_user"}
    }
    params2 = {
        k: v
        for k, v in task2.items()
        if k not in {"name", "register", "tags", "when", "become", "become_user"}
    }

    return params1 == params2


def _extract_module_name(task: dict[str, Any]) -> str | None:
    """Extract the Ansible module name from a task."""
    # Check for module keys like 'apt', 'service', 'package', etc.
    ansible_modules = {
        "apt",
        "yum",
        "dnf",
        "zypper",
        "pacman",
        "package",
        "service",
        "systemd",
        "shell",
        "command",
        "debug",
        "copy",
        "template",
        "file",
        "directory",
        "lineinfile",
        "user",
        "group",
        "stat",
        "wait_for",
        "uri",
        "get_url",
    }

    for key in task:
        if key in ansible_modules:
            return key

    return None


def consolidate_duplicate_tasks(
    tasks: list[dict[str, Any]], duplicates: list[tuple[int, int]]
) -> list[dict[str, Any]]:
    """
    Consolidate duplicate tasks by removing duplicates.

    Args:
        tasks: List of task dictionaries.
        duplicates: List of (index1, index2) tuples for duplicates.

    Returns:
        Deduplicated task list.

    """
    # Mark indices to remove (keep first occurrence of duplicates)
    indices_to_remove = set()
    for _, j in duplicates:
        indices_to_remove.add(j)

    return [task for i, task in enumerate(tasks) if i not in indices_to_remove]


def optimize_task_loops(
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Consolidate repetitive tasks into loops where possible.

    Example: Multiple 'apt: name=package state=present' tasks
             → Single task with 'loop' over package list.

    Args:
        tasks: List of task dictionaries.

    Returns:
        Optimized task list with loop consolidation.

    """
    optimized: list[dict[str, Any]] = []
    i = 0

    while i < len(tasks):
        current = tasks[i]
        module = _extract_module_name(current)

        # Look for consecutive similar tasks
        similar_group = [current]
        j = i + 1

        while j < len(tasks):
            next_task = tasks[j]
            if _extract_module_name(next_task) != module:
                break

            # Check if parameters differ only in loop variable
            if _can_consolidate_to_loop(current, next_task):
                similar_group.append(next_task)
                j += 1
            else:
                break  # pragma: no cover

        # If we found 3+ similar tasks, consolidate to loop
        if len(similar_group) >= 3:
            looped_task = _create_loop_consolidated_task(similar_group, module)
            optimized.append(looped_task)
            i = j
        else:
            optimized.append(current)
            i += 1

    return optimized


def _can_consolidate_to_loop(task1: dict[str, Any], task2: dict[str, Any]) -> bool:
    """
    Check if two tasks can be consolidated into a single loop task.

    Args:
        task1: First task.
        task2: Second task.

    Returns:
        True if tasks can be consolidated, False otherwise.

    """
    # For now, simple heuristic: tasks with same module name
    # can be consolidation candidates (would need more sophisticated
    # analysis for production use)
    return _extract_module_name(task1) == _extract_module_name(task2)


def _create_loop_consolidated_task(
    tasks: list[dict[str, Any]], module: str | None
) -> dict[str, Any]:
    """
    Create a consolidated task with loop from similar tasks.

    Args:
        tasks: List of similar tasks.
        module: The Ansible module name.

    Returns:
        Consolidated task dictionary with loop.

    """
    if not tasks:
        return {}

    # Use first task as template
    base_task = dict(tasks[0])
    base_task["name"] = f"Consolidate: {module or 'task'}"

    # Extract loop variables (e.g., package names from apt module)
    loop_items = []
    if module and (module == "apt" or module == "package"):
        for task in tasks:
            module_data = task.get(module, {})
            if isinstance(module_data, dict) and "name" in module_data:
                loop_items.append(module_data.get("name"))

    if loop_items:
        base_task["loop"] = loop_items
        base_task["vars"] = {"item_name": "{{ item }}"}

    return base_task


def calculate_optimization_metrics(
    original_tasks: list[dict[str, Any]], optimized_tasks: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Calculate metrics for playbook optimization.

    Args:
        original_tasks: Original task list.
        optimized_tasks: Optimized task list.

    Returns:
        Dictionary with optimization metrics.

    """
    original_count = len(original_tasks)
    optimized_count = len(optimized_tasks)
    reduction = original_count - optimized_count

    return {
        "original_task_count": original_count,
        "optimized_task_count": optimized_count,
        "tasks_reduced": reduction,
        "reduction_percentage": (
            (reduction / original_count * 100) if original_count > 0 else 0
        ),
        "optimization_applied": reduction > 0,
    }
