"""Constants used throughout SousChef."""

__all__ = [
    "ANSIBLE_SERVICE_MODULE",
    "METADATA_FILENAME",
    "ERROR_PREFIX",
    "NODE_PREFIX",
    "CHEF_RECIPE_PREFIX",
    "CHEF_ROLE_PREFIX",
    "REGEX_WHITESPACE_QUOTE",
    "REGEX_QUOTE_DO_END",
    "REGEX_RESOURCE_BRACKET",
    "REGEX_ERB_OUTPUT",
    "REGEX_ERB_CONDITION",
    "REGEX_ERB_NODE_ATTR",
    "REGEX_ERB_IF_START",
    "REGEX_ERB_UNLESS",
    "REGEX_ERB_ELSE",
    "REGEX_ERB_ELSIF",
    "REGEX_ERB_END",
    "REGEX_ERB_EACH",
    "REGEX_WORD_SYMBOLS",
    "REGEX_RUBY_INTERPOLATION",
    "JINJA2_VAR_REPLACEMENT",
    "JINJA2_NODE_ATTR_REPLACEMENT",
    "JINJA2_IF_START",
    "JINJA2_IF_NOT",
    "JINJA2_ELSE",
    "JINJA2_ELIF",
    "JINJA2_ENDIF",
    "JINJA2_FOR",
    "ERB_PATTERNS",
    "INSPEC_END_INDENT",
    "INSPEC_SHOULD_EXIST",
    "ERROR_FILE_NOT_FOUND",
    "ERROR_IS_DIRECTORY",
    "ERROR_PERMISSION_DENIED",
    "RESOURCE_MAPPINGS",
    "ACTION_TO_STATE",
]

# Ansible module names
ANSIBLE_SERVICE_MODULE = "ansible.builtin.service"

# File names
METADATA_FILENAME = "metadata.rb"

# Common prefixes
ERROR_PREFIX = "Error:"
NODE_PREFIX = "node["
CHEF_RECIPE_PREFIX = "recipe["
CHEF_ROLE_PREFIX = "role["

# Regular expression patterns for Ruby/ERB parsing
REGEX_WHITESPACE_QUOTE = r"\s+['\"]?"
REGEX_QUOTE_DO_END = r"['\"]?\s+do\s*([^\n]{0,15000})\nend"
REGEX_RESOURCE_BRACKET = r"(\w+)\[([^\]]+)\]"
REGEX_ERB_OUTPUT = r"<%=\s*([^%]{1,200}?)\s*%>"
REGEX_ERB_CONDITION = r"[^%]{1,200}?"
REGEX_ERB_NODE_ATTR = rf"<%=\s*node\[(['\"])({REGEX_ERB_CONDITION})\1\]\s*%>"
REGEX_ERB_IF_START = rf"<%\s*if\s+({REGEX_ERB_CONDITION})\s*%>"
REGEX_ERB_UNLESS = rf"<%\s*unless\s+({REGEX_ERB_CONDITION})\s*%>"
REGEX_ERB_ELSE = r"<%\s*else\s*%>"
REGEX_ERB_ELSIF = rf"<%\s*elsif\s+({REGEX_ERB_CONDITION})\s*%>"
REGEX_ERB_END = r"<%\s*end\s*%>"
REGEX_ERB_EACH = rf"<%\s*({REGEX_ERB_CONDITION})\.each\s+do\s+\|(\w+)\|\s*%>"
REGEX_WORD_SYMBOLS = r"[\w.\[\]'\"]+"
REGEX_RUBY_INTERPOLATION = r"#\{([^}]+)\}"

# Jinja2 template replacements
JINJA2_VAR_REPLACEMENT = r"{{ \1 }}"
JINJA2_NODE_ATTR_REPLACEMENT = r"{{ \2 }}"
JINJA2_IF_START = r"{% if \1 %}"
JINJA2_IF_NOT = r"{% if not \1 %}"
JINJA2_ELSE = r"{% else %}"
JINJA2_ELIF = r"{% elif \1 %}"
JINJA2_ENDIF = r"{% endif %}"
JINJA2_FOR = r"{% for \2 in \1 %}"

# ERB to Jinja2 pattern mappings
ERB_PATTERNS = {
    # Variable output: <%= var %> -> {{ var }}
    "output": (REGEX_ERB_OUTPUT, JINJA2_VAR_REPLACEMENT),
    # Variable with node prefix: <%= node['attr'] %> -> {{ attr }}
    "node_attr": (REGEX_ERB_NODE_ATTR, JINJA2_NODE_ATTR_REPLACEMENT),
    # If statements: <% if condition %> -> {% if condition %}
    "if_start": (REGEX_ERB_IF_START, JINJA2_IF_START),
    # Unless (negated if): <% unless condition %> -> {% if not condition %}
    "unless": (REGEX_ERB_UNLESS, JINJA2_IF_NOT),
    # Else: <% else %> -> {% else %}
    "else": (REGEX_ERB_ELSE, JINJA2_ELSE),
    # Elsif: <% elsif condition %> -> {% elif condition %}
    "elsif": (REGEX_ERB_ELSIF, JINJA2_ELIF),
    # End: <% end %> -> {% endif %}
    "end": (REGEX_ERB_END, JINJA2_ENDIF),
    # Each loop: <% array.each do |item| %> -> {% for item in array %}
    # Use [^%]{1,200} to prevent matching across %> boundaries and ReDoS
    "each": (REGEX_ERB_EACH, JINJA2_FOR),
}

# InSpec output formatting
INSPEC_END_INDENT = "  end"
INSPEC_SHOULD_EXIST = "    it { should exist }"

# Error message templates
ERROR_FILE_NOT_FOUND = "Error: File not found at {path}"
ERROR_IS_DIRECTORY = "Error: {path} is a directory, not a file"
ERROR_PERMISSION_DENIED = "Error: Permission denied for {path}"

# Chef resource to Ansible module mappings
RESOURCE_MAPPINGS = {
    "package": "ansible.builtin.package",
    "apt_package": "ansible.builtin.apt",
    "yum_package": "ansible.builtin.yum",
    "service": ANSIBLE_SERVICE_MODULE,
    "systemd_unit": "ansible.builtin.systemd",
    "template": "ansible.builtin.template",
    "file": "ansible.builtin.file",
    "directory": "ansible.builtin.file",
    "execute": "ansible.builtin.command",
    "bash": "ansible.builtin.shell",
    "script": "ansible.builtin.script",
    "user": "ansible.builtin.user",
    "group": "ansible.builtin.group",
    "cron": "ansible.builtin.cron",
    "mount": "ansible.builtin.mount",
    "git": "ansible.builtin.git",
    "remote_file": "ansible.builtin.get_url",
}

# Chef action to Ansible state mappings
ACTION_TO_STATE = {
    "create": "present",
    "delete": "absent",
    "remove": "absent",
    "install": "present",
    "upgrade": "latest",
    "purge": "absent",
    "enable": "started",
    "disable": "stopped",
    "start": "started",
    "stop": "stopped",
    "restart": "restarted",
    "reload": "reloaded",
}
