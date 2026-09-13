"""Platform-neutral default configuration for a new VoiceFlow installation."""


DEFAULT_CONFIG = {
    "hotkey": {"key": "ctrl_l"},
    "asr": {
        "engine": "auto",
        "model": "",
        "language": "en",
        "compute_type_gpu": "float16",
        "compute_type_cpu": "int8",
    },
    "llm": {
        "docker_llm_url": "http://localhost:12434/engines/llama.cpp/v1",
        "docker_llm_model": "",
        "ollama_model": "llama3.2:3b",
        "ollama_base_url": "http://localhost:11434",
        "temperature": 0.1,
        "max_tokens": 500,
        "cleanup_level": "light",
    },
    "injection": {
        "method": "auto",
    },
    "ui": {
        "show_notification": True,
        "notification_duration": 3,
        "dashboard_port": 57327,
    },
}
