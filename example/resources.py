from random import randrange

_PATH = "/local/cards/"


def resources(module, module_type):
    version = f"?v={randrange(1000000)}"
    # This works to, the lib can handle lists, dicts, etc as return values:
    # return [{'url': f"{_PATH}/{module}{version}", "type": module_type}]
    return f"url: {_PATH}/{module}{version}\ntype: {module_type}"
