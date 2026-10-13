"""Trusted local research F/H/C adapter; optional ML dependencies load lazily."""
from pathlib import Path

AXES = ('Formality', 'Humor', 'Curiosity')
ROOT = Path(__file__).resolve().parents[1]


class ResearchedAxisModel:
    def __init__(self, bundle, *, encoder_path=None, encoder=None):
        if bundle.get('schema_version') != 1:
            raise ValueError('Unsupported researched model schema')
        if set(bundle.get('heads', {})) != set(AXES) or set(bundle.get('configs', {})) != set(AXES):
            raise ValueError('Artifact must contain all three F/H/C heads')
        if any(c.get('family') not in ('tfidf', 'embedding', 'combined', 'embedding_rules') for c in bundle['configs'].values()):
            raise ValueError('Unsupported feature family')
        self.bundle = bundle
        self.encoder = encoder
        path = Path(encoder_path or bundle['encoder_path'])
        self.encoder_path = path if path.is_absolute() else ROOT / path

    @classmethod
    def from_artifact(cls, path, *, encoder_path=None, encoder=None):
        """Only call with trusted local joblib files; pickle is not upload-safe."""
        import joblib
        bundle = joblib.load(path)
        if bundle.get('schema_version') == 2:
            from ai.selected_fhc_model import SelectedFHCModel
            return SelectedFHCModel(bundle, encoder_path=encoder_path, encoder=encoder)
        return cls(bundle, encoder_path=encoder_path, encoder=encoder)

    def predict_many(self, texts):
        if not isinstance(texts, list) or any(not isinstance(t, str) or not t.strip() for t in texts):
            raise ValueError('Expected a list of nonempty utterances')
        if not texts:
            return []
        import numpy as np
        from scipy.sparse import hstack, csr_matrix
        from sklearn.preprocessing import normalize
        families = {c['family'] for c in self.bundle['configs'].values()}
        features = {}
        if families & {'tfidf', 'combined'}:
            vocabulary = self.bundle['vocabulary']
            lex = hstack([vocabulary['word'].transform(texts), vocabulary['char'].transform(texts)]).tocsr()
            features['tfidf'] = lex
        if families & {'embedding', 'combined', 'embedding_rules'}:
            if self.encoder is None:
                from ai.embedding_axis_adapter import EmbeddingAxisAdapter
                self.encoder = EmbeddingAxisAdapter(model_name=str(self.encoder_path), local_files_only=True)
            embed = self.encoder._encode(texts)
            if embed.ndim != 2 or len(embed) != len(texts) or not np.isfinite(embed).all():
                raise ValueError('Invalid encoder features')
            features['embedding'] = embed
        if 'embedding_rules' in families:
            from ai.analyzer import analyze_utterance
            rule_values = [analyze_utterance(t) for t in texts]
            rules = np.array([[r[a] for a in AXES] for r in rule_values], dtype=float) / 100.
            features['embedding_rules'] = np.hstack([embed, rules])
        if 'combined' in families:
            features['combined'] = hstack([normalize(lex), csr_matrix(normalize(embed))]).tocsr() / np.sqrt(2.)
        predictions = {}
        for axis in AXES:
            values = np.asarray(self.bundle['heads'][axis].predict(features[self.bundle['configs'][axis]['family']]))
            if values.shape != (len(texts),) or not np.isfinite(values).all():
                raise ValueError('Invalid model prediction')
            predictions[axis] = np.round(np.clip(values, 0, 100) / 5) * 5
        return [{a: int(predictions[a][i]) for a in AXES} for i in range(len(texts))]

    def predict_partial(self, utterance):
        return self.predict_many([utterance])[0]
