# Général

Projet d'implémentation en test d'un algorithme réglementaire déterminant l'éligibilité au droit de vote en France, conforme au Code électoral (Art. L.2 à L.7 et L.O. 227-1).

## Contexte

Ce package implémente les règles du droit de vote issues du Code électoral français et de l'article 88-3 de la Constitution. Il fait partie d'un écosystème d'algorithmes réglementaires (`regalgo`) visant à formaliser et coder des règles de droit en source ouverte.

Les métadonnées sont alignées sur les vocabulaires européens :
- [Core Person Vocabulary (ISA²)](https://joinup.ec.europa.eu/collection/semantic-interoperability-community-semic/solution/core-person-vocabulary)
- [Core Criterion and Evidence Vocabulary (CCCEV)](https://joinup.ec.europa.eu/collection/semantic-interoperability-community-semic/solution/core-criterion-and-evidence-vocabulary)
- [CPRMV 0.4.0](https://standaarden.open-regels.nl/standards/cprmv/0.4.0/)

## Règles implémentées

### Élections nationales (défaut)

Conditions cumulatives (Art. L.2 à L.7 du Code électoral) :

| Condition | Source |
|---|---|
| Nationalité française | Art. L.2 |
| Âge ≥ 18 ans | Art. L.3 |
| Non privé de droits civiques | Art. L.5, L.6 |
| Inscrit sur les listes électorales | Art. L.7 |

### Élections municipales

La condition de nationalité est élargie (Art. 88-3 C° / L.O. 227-1) :
- Nationalité française **ou** (citoyen UE + domicilié en France)

Les autres conditions (âge, capacité civique, inscription) restent identiques.

## Installation

```bash
pip install regalgo-civique-droit-vote
```

## Utilisation

### Via `AlgoInput` (entrée directe)

```python
from regalgo_civique_droit_vote import DroitVoteAlgorithm, AlgoInput

algo = DroitVoteAlgorithm()

result = algo.compute(AlgoInput(data={
    "nationalite_francaise": True,
    "age": 25,
    "capacite_civique": True,
    "inscrit_listes_electorales": True,
}))

print(result.value)  # True
```

### Via `PersonInput` (Core Vocabularies EU)

```python
from datetime import date
from regalgo_civique_droit_vote import DroitVoteAlgorithm, PersonInput

person = PersonInput(
    cv_nationality="FR",               # ISO 3166-1 alpha-2
    schema_birth_date=date(1990, 6, 15),
    cccev_civil_rights_intact=True,
    cccev_electoral_list_registered=True,
)

algo = DroitVoteAlgorithm()
result = algo.compute(person.to_algo_input())

print(result.value)        # True
print(result.metadata)     # détail des conditions évaluées
```

### Élection municipale — citoyen UE résident en France

```python
person = PersonInput(
    cv_nationality="DE",
    schema_birth_date=date(1985, 3, 20),
    cccev_civil_rights_intact=True,
    cccev_electoral_list_registered=True,
    cv_domicile_country="FR",
)

result = algo.compute(person.to_algo_input(context={"type_election": "municipale"}))
print(result.value)  # True
```

## Structure de la sortie (`AlgoResult`)

```python
AlgoResult(
    value=True,                      # résultat booléen
    algo_id="civique.droit-vote.v1", # identifiant de l'algorithme
    regulation={...},                # référence au Code électoral
    inputs_snapshot={...},           # instantané des entrées utilisées
    metadata={
        "type_election": "nationale",
        "conditions": {
            "eligible_nationalite": True,
            "nationalite_francaise": True,
            "citoyennete_ue_avec_domicile_france": False,
            "age_suffisant": True,
            "capacite_civique": True,
            "inscrit_listes_electorales": True,
        },
    },
)
```

## Tests

```bash
pytest
```

## Références légales

- [Code électoral — Art. L.2 à L.7, L.O. 227-1](https://www.legifrance.gouv.fr/codes/id/LEGITEXT000006070239/)
- [Constitution du 4 octobre 1958 — Art. 88-3](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000006527438/)
