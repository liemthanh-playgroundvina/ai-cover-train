from main import run_preprocess_script, run_extract_script, run_train_script


def train_voice(voice_id=str, audio_dir=str, step: int = 50):
    """
    Train a voice

    rvc: v2
    batch_size : 8 = 6GB VRAM 3090ti
    audio_dir : 4 audio files
    epoch: 50

    """
    model_name = voice_id
    rvc_version = "v2"
    total_epoch = step
    save_every_epoch = total_epoch + 1
    save_only_latest = False
    save_every_weights = False
    sampling_rate = 32000
    batch_size = 8
    gpu = 0
    pitch_guidance = True
    overtraining_detector = False
    overtraining_threshold = 1

    pretrained = True
    custom_pretrained = True
    g_pretrained_path = "models/f0Ov2Super32kG.pth"
    d_pretrained_path = "models/f0Ov2Super32kD.pth"

    # Preprocess
    run_preprocess_script(voice_id, audio_dir, sampling_rate)
    # Extract
    run_extract_script(voice_id, rvc_version, "rmvpe", 128, sampling_rate)

    # local_vars = locals()
    # for var_name, value in local_vars.items():
    #     print(f'"{var_name}": {value}')

    # Train
    path_model, path_index = run_train_script(
        model_name,
        rvc_version,
        save_every_epoch,
        save_only_latest,
        save_every_weights,
        total_epoch,
        sampling_rate,
        batch_size,
        gpu,
        pitch_guidance,
        overtraining_detector,
        overtraining_threshold,
        pretrained,
        custom_pretrained,
        g_pretrained_path,
        d_pretrained_path
    )

    return path_model, path_index


# path_model, path_index = train_voice("123", "./dataset/123")
# print(path_model, path_index)
