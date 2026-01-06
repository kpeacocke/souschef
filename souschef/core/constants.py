"""Constants used throughout SousChef."""

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

# InSpec output formatting
INSPEC_END_INDENT = "  end"
INSPEC_SHOULD_EXIST = "    it { should exist }"

# Error message templates
ERROR_FILE_NOT_FOUND = "Error: File not found at {path}"
ERROR_IS_DIRECTORY = "Error: {path} is a directory, not a file"
ERROR_PERMISSION_DENIED = "Error: Permission denied for {path}"
