"""Portable per-axis composition of trusted, separately selected F/H/C heads."""
from pathlib import Path

AXES = ('Formality', 'Humor', 'Curiosity')
ROOT = Path(__file__).resolve().parents[1]


class SelectedFHCModel:
    def __init__(self, bundle, *, encoder_path=None, encoder=None):
        if bundle.get('schema_version') != 2 or set(bundle.get('axis_routing', {})) != set(AXES):
            raise ValueError('Invalid selected F/H/C model schema')
        for axis, key in bundle['axis_routing'].items():
            component = bundle['components'].get(key)
            if not component or component.get('family') not in ('tfidf', 'embedding', 'combined', 'embedding_rules') or 'base' not in component:
                raise ValueError('Invalid selected model component')
        if bundle.get('rule_code_sha256') and any(bundle['components'][key]['family'] == 'embedding_rules' for key in bundle['axis_routing'].values()):
            import hashlib
            actual = hashlib.sha256((ROOT / 'ai/analyzer.py').read_bytes()).hexdigest()
            if actual != bundle['rule_code_sha256']:
                raise ValueError('Linguistic rule source changed since selected model training')
        self.bundle, self.encoder = bundle, encoder
        p = Path(encoder_path or bundle['encoder_path'])
        self.encoder_path = p if p.is_absolute() else ROOT / p

    @classmethod
    def from_artifact(cls, path, *, encoder_path=None, encoder=None):
        import joblib
        return cls(joblib.load(path), encoder_path=encoder_path, encoder=encoder)

    def predict_many(self, texts):
        if not isinstance(texts, list) or any(not isinstance(t, str) or not t.strip() for t in texts):
            raise ValueError('Expected nonempty text strings')
        if not texts:
            return []
        import numpy as np
        from scipy.sparse import csr_matrix, hstack
        from sklearn.preprocessing import normalize
        components = self.bundle['components']
        families = {components[key]['family'] for key in self.bundle['axis_routing'].values()}
        embed = None
        if families - {'tfidf'}:
            if self.encoder is None:
                from ai.embedding_axis_adapter import EmbeddingAxisAdapter
                self.encoder = EmbeddingAxisAdapter(model_name=str(self.encoder_path), local_files_only=True)
            embed = self.encoder._encode(texts)
            if embed.ndim != 2 or len(embed) != len(texts) or not np.isfinite(embed).all():
                raise ValueError('Invalid encoder features')
        features, output = {}, {}
        for axis, key in self.bundle['axis_routing'].items():
            c = components[key]
            if key not in features:
                family = c['family']
                if family in ('tfidf', 'combined'):
                    v = c['vocabulary']
                    lex = hstack([v['word'].transform(texts), v['char'].transform(texts)]).tocsr()
                if family == 'tfidf':
                    x = lex
                elif family == 'embedding':
                    x = embed
                elif family == 'combined':
                    x = hstack([normalize(lex), csr_matrix(normalize(embed))]).tocsr() / np.sqrt(2.)
                else:
                    from ai.analyzer import analyze_utterance
                    raw = [analyze_utterance(t) for t in texts]
                    x = np.hstack([embed, np.array([[r[a] for a in AXES] for r in raw], dtype=float) / 100.])
                features[key] = x
            values = np.asarray(c['base'].predict(features[key]))
            if c.get('residual') is not None:
                values = values + np.asarray(c['residual'].predict(features[key]))
            if values.shape != (len(texts),) or not np.isfinite(values).all():
                raise ValueError('Invalid head predictions')
            output[axis] = np.round(np.clip(values, 0, 100) / 5) * 5
        return [{a: int(output[a][i]) for a in AXES} for i in range(len(texts))]

    def predict_partial(self, utterance):
        return self.predict_many([utterance])[0]
