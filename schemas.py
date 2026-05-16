"""
JSON Schema Definitions for Quiz Question Validation
"""

# ================== MCQ SCHEMA ================== #
MCQ_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "MCQ Question",
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "type", "stem", "input", "answer"],
    "properties": {
        "id": {
            "type": "integer",
            "minimum": 1
        },
        "type": {
            "const": "mcq"
        },
        "stem": {
            "type": "object",
            "additionalProperties": False,
            "required": ["latex", "html"],
            "properties": {
                "latex": {"type": "string", "minLength": 1},
                "html": {"type": "string", "minLength": 1},
                "feedback": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["latex", "html"],
                    "properties": {
                        "latex": {"type": "string", "minLength": 1},
                        "html": {"type": "string", "minLength": 1}
                    }
                }
            }
        },
        "image": {
            "type": "object",
            "additionalProperties": False,
            "required": ["src", "alt"],
            "properties": {
                "src": {"type": "string", "minLength": 1},
                "alt": {"type": "string"}
            }
        },
        "input": {
            "type": "object",
            "additionalProperties": False,
            "required": ["options", "shuffle"],
            "properties": {
                "options": {
                    "type": "array",
                    "minItems": 2,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["id", "latex", "html"],
                        "properties": {
                            "id": {
                                "type": "string",
                                "pattern": "^opt[1-9][0-9]*$"
                            },
                            "latex": {"type": "string", "minLength": 1},
                            "html": {"type": "string", "minLength": 1}
                        }
                    }
                },
                "shuffle": {"type": "boolean"}
            }
        },
        "answer": {
            "type": "object",
            "additionalProperties": False,
            "required": ["correct_option_id"],
            "properties": {
                "correct_option_id": {
                    "type": "string",
                    "pattern": "^opt[1-9][0-9]*$"
                }
            }
        },
        "topic": {"type": "string"},
        "subtopic": {"type": "string"},
        "level": {"type": "string"}
    }
}

# ================== FILL SCHEMA ================== #
FILL_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Fill in the Blank Question",
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "type", "stem", "input", "answer"],
    "properties": {
        "id": {
            "type": "integer",
            "minimum": 1
        },
        "type": {
            "const": "fill"
        },
        "stem": {
            "type": "object",
            "additionalProperties": False,
            "required": ["latex", "html"],
            "properties": {
                "latex": {"type": "string", "minLength": 1},
                "html": {"type": "string", "minLength": 1},
                "feedback": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["latex", "html"],
                    "properties": {
                        "latex": {"type": "string", "minLength": 1},
                        "html": {"type": "string", "minLength": 1}
                    }
                }
            }
        },
        "image": {
            "type": "object",
            "additionalProperties": False,
            "required": ["src", "alt"],
            "properties": {
                "src": {"type": "string", "minLength": 1},
                "alt": {"type": "string"}
            }
        },
        "input": {
            "type": "object",
            "additionalProperties": False,
            "required": ["blanks"],
            "properties": {
                "blanks": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["id", "response_type"],
                        "properties": {
                            "id": {
                                "type": "string",
                                "pattern": "^blank[1-9][0-9]*$"
                            },
                            "input_label": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["latex", "html"],
                                "properties": {
                                    "latex": {"type": "string", "minLength": 1},
                                    "html": {"type": "string", "minLength": 1}
                                }
                            },
                            "label_after": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["latex", "html"],
                                "properties": {
                                    "latex": {"type": "string", "minLength": 1},
                                    "html": {"type": "string", "minLength": 1}
                                }
                            },
                            "response_type": {
                                "type": "string",
                                "enum": ["text", "numeric", "fraction"]
                            },
                            "placeholder": {
                                "type": "string"
                            }
                        }
                    }
                }
            }
        },
        "answer": {
            "type": "object",
            "additionalProperties": False,
            "required": ["correct"],
            "properties": {
                "correct": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["blank_id", "response_type"],
                        "properties": {
                            "blank_id": {
                                "type": "string",
                                "pattern": "^blank[1-9][0-9]*$"
                            },
                            "response_type": {
                                "type": "string",
                                "enum": ["text", "numeric", "fraction"]
                            },
                            "accepted_text": {
                                "type": "array",
                                "minItems": 1,
                                "items": {
                                    "type": "string",
                                    "minLength": 1
                                }
                            },
                            "accepted_numeric": {
                                "type": "array",
                                "minItems": 1,
                                "items": {
                                    "type": "number"
                                }
                            },
                            "accepted_fraction": {
                                "type": "array",
                                "minItems": 1,
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["numerator", "denominator"],
                                    "properties": {
                                        "numerator": {
                                            "type": "integer"
                                        },
                                        "denominator": {
                                            "type": "integer",
                                            "not": {"const": 0}
                                        }
                                    }
                                }
                            },
                            "case_sensitive": {
                                "type": "boolean"
                            }
                        },
                        "allOf": [
                            {
                                "if": {
                                    "properties": {
                                        "response_type": {"const": "text"}
                                    }
                                },
                                "then": {
                                    "required": ["accepted_text"]
                                }
                            },
                            {
                                "if": {
                                    "properties": {
                                        "response_type": {"const": "numeric"}
                                    }
                                },
                                "then": {
                                    "required": ["accepted_numeric"]
                                }
                            },
                            {
                                "if": {
                                    "properties": {
                                        "response_type": {"const": "fraction"}
                                    }
                                },
                                "then": {
                                    "required": ["accepted_fraction"]
                                }
                            }
                        ]
                    }
                }
            }
        },
        "topic": {"type": "string"},
        "subtopic": {"type": "string"},
        "level": {"type": "string"}
    }
}

# ================== MR SCHEMA ================== #
MR_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Multiple Response Question",
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "type", "stem", "input", "answer"],
    "properties": {
        "id": {
            "type": "integer",
            "minimum": 1
        },
        "type": {
            "const": "mr"
        },
        "stem": {
            "type": "object",
            "additionalProperties": False,
            "required": ["latex", "html"],
            "properties": {
                "latex": {"type": "string", "minLength": 1},
                "html": {"type": "string", "minLength": 1},
                "feedback": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["latex", "html"],
                    "properties": {
                        "latex": {"type": "string", "minLength": 1},
                        "html": {"type": "string", "minLength": 1}
                    }
                }
            }
        },
        "image": {
            "type": "object",
            "additionalProperties": False,
            "required": ["src", "alt"],
            "properties": {
                "src": {"type": "string", "minLength": 1},
                "alt": {"type": "string"}
            }
        },
        "input": {
            "type": "object",
            "additionalProperties": False,
            "required": ["options", "shuffle"],
            "properties": {
                "options": {
                    "type": "array",
                    "minItems": 2,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["id", "latex", "html"],
                        "properties": {
                            "id": {
                                "type": "string",
                                "pattern": "^opt[1-9][0-9]*$"
                            },
                            "latex": {"type": "string", "minLength": 1},
                            "html": {"type": "string", "minLength": 1}
                        }
                    }
                },
                "shuffle": {"type": "boolean"}
            }
        },
        "answer": {
            "type": "object",
            "additionalProperties": False,
            "required": ["correct_option_ids"],
            "properties": {
                "correct_option_ids": {
                    "type": "array",
                    "minItems": 2,
                    "items": {
                        "type": "string",
                        "pattern": "^opt[1-9][0-9]*$"
                    }
                }
            }
        },
        "topic": {"type": "string"},
        "subtopic": {"type": "string"},
        "level": {"type": "string"}
    }
}

# ================== OHS SCHEMA ================== #
OHS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "One HotSpot Question",
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "type", "image", "input", "answer"],
    "properties": {
        "id": {
            "type": "integer",
            "minimum": 1
        },
        "type": {
            "const": "ohs"
        },
        "stem": {
            "type": "object",
            "additionalProperties": False,
            "required": ["latex", "html"],
            "properties": {
                "latex": {"type": "string", "minLength": 1},
                "html": {"type": "string", "minLength": 1},
                "feedback": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["latex", "html"],
                    "properties": {
                        "latex": {"type": "string", "minLength": 1},
                        "html": {"type": "string", "minLength": 1}
                    }
                }
            }
        },
        "image": {
            "type": "object",
            "additionalProperties": False,
            "required": ["src", "alt", "hotspot"],
            "properties": {
                "src": {"type": "string", "minLength": 1},
                "alt": {"type": "string"},
                "hotspot": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "x", "y", "width", "height"],
                    "properties": {
                        "id": {
                            "type": "string",
                            "pattern": "^hs1$"
                        },
                        "x": {"type": "number", "minimum": 0},
                        "y": {"type": "number", "minimum": 0},
                        "width": {"type": "number", "minimum": 1},
                        "height": {"type": "number", "minimum": 1}
                    }
                }
            }
        },
        "input": {
            "type": "object",
            "additionalProperties": False,
            "properties": {}
        },
        "answer": {
            "type": "object",
            "additionalProperties": False,
            "required": ["correct_hotspot_id"],
            "properties": {
                "correct_hotspot_id": {
                    "type": "string",
                    "const": "hs1"
                }
            }
        },
        "topic": {"type": "string"},
        "subtopic": {"type": "string"},
        "level": {"type": "string"}
    }
}
