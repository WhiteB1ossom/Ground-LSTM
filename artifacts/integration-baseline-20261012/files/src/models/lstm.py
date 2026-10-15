"""Small forward-only Keras LSTM. TensorFlow is imported only for ML commands."""


def build_lstm(shape: tuple[int, int], class_count: int, config: dict):
    import tensorflow as tf
    model = tf.keras.Sequential([tf.keras.Input(shape=shape, name="sensor_sequence")], name="causal_lstm")
    for layer in range(config["model"]["num_layers"]):
        model.add(tf.keras.layers.LSTM(config["model"]["hidden_units"], return_sequences=layer < config["model"]["num_layers"] - 1, name=f"lstm_{layer + 1}"))
        if config["model"]["dropout"]:
            model.add(tf.keras.layers.Dropout(config["model"]["dropout"], seed=config["seed"] + layer))
    binary = class_count == 2
    model.add(tf.keras.layers.Dense(1 if binary else class_count, activation="sigmoid" if binary else "softmax", name="risk_output"))
    metrics = [tf.keras.metrics.Precision(name="precision"), tf.keras.metrics.Recall(name="recall"), tf.keras.metrics.AUC(curve="PR", name="pr_auc")] if binary else [tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy")]
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=config["training"]["learning_rate"]),
                  loss="binary_crossentropy" if binary else "sparse_categorical_crossentropy", metrics=metrics)
    return model
