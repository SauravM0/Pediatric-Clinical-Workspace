"""Optional local AI: a CPU bone-age screening model (ONNX Runtime).

This is a Greulich-Pyle-style WHOLE-IMAGE estimate, NOT TW3-RUS staging. It is a
screening suggestion the doctor verifies — never the authoritative TW3 result
(directive §17, §28). Inference needs only onnxruntime + Pillow + numpy; training
(train_boneage.py) additionally needs torch and is a dev-time step.
"""
