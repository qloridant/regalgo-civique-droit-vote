from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

# États membres de l'UE — ISO 3166-1 alpha-2 (27 membres, 2024)
EU_MEMBER_STATES: frozenset[str] = frozenset({
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI",
    "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
    "NL", "PL", "PT", "RO", "SE", "SI", "SK",
})


# --- Structures de données standard ---

@dataclass
class AlgoInput:
    """Entrée normalisée d'un algorithme réglementaire."""
    data: dict[str, Any]
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class PersonInput:
    """
    Représentation d'une personne alignée sur les Core Vocabularies EU ISA².

    Préfixes :
      cv:     http://data.europa.eu/m8g/       (Core Person Vocabulary)
      schema: http://schema.org/
      cccev:  http://data.europa.eu/m8g/cccev/ (Core Criterion & Evidence Vocabulary)
    """

    # cv:nationality — code ISO 3166-1 alpha-2 (ex. "FR", "DE")
    cv_nationality: str

    # schema:birthDate — date de naissance, l'âge est calculé à la volée
    schema_birth_date: date

    # CCCEV criterion : non privé de ses droits civiques (Art. L.5, L.6)
    cccev_civil_rights_intact: bool

    # CCCEV criterion : inscrit sur les listes électorales (Art. L.7 / L.O. 227-1)
    cccev_electoral_list_registered: bool

    # cv:domicile → adminUnitL1 — pays de résidence, ISO 3166-1 alpha-2 (défaut "FR")
    cv_domicile_country: str = "FR"

    def to_algo_input(self, context: dict[str, Any] | None = None) -> AlgoInput:
        """Convertit vers AlgoInput en calculant l'âge depuis schema:birthDate."""
        today = date.today()
        age = today.year - self.schema_birth_date.year - (
            (today.month, today.day)
            < (self.schema_birth_date.month, self.schema_birth_date.day)
        )
        return AlgoInput(
            data={
                "nationalite_francaise": self.cv_nationality.upper() == "FR",
                "citoyennete_ue": self.cv_nationality.upper() in EU_MEMBER_STATES,
                "domicile_france": self.cv_domicile_country.upper() == "FR",
                "age": age,
                "capacite_civique": self.cccev_civil_rights_intact,
                "inscrit_listes_electorales": self.cccev_electoral_list_registered,
            },
            context=context or {},
        )


@dataclass
class AlgoResult:
    """Sortie normalisée d'un algorithme réglementaire."""
    value: Any
    algo_id: str
    regulation: dict[str, str]
    inputs_snapshot: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


# --- Implémentation de l'algorithme ---

class DroitVoteAlgorithm:
    """
    Éligibilité au droit de vote en France selon le Code électoral.

    Élections nationales (défaut) — conditions cumulatives Art. L.2 à L.7 :
        - Nationalité française
        - 18 ans ou plus
        - Non privé de droits civiques
        - Inscrit sur les listes électorales

    Élections municipales (context["type_election"] == "municipale") :
        - Nationalité française OU (citoyen UE + domicile en France)  ← Art. 88-3 C° / L.O. 227-1
        - Mêmes conditions d'âge, capacité et inscription
    """

    def __init__(self) -> None:
        _meta_path = Path(__file__).parent / "metadata.json"
        self._metadata = json.loads(_meta_path.read_text())

    @property
    def algo_id(self) -> str:
        return self._metadata["dct:identifier"]

    @property
    def regulation(self) -> dict[str, str]:
        return self._metadata["cprmv:isBasedOn"]

    def compute(self, algo_input: AlgoInput) -> AlgoResult:
        """
        Détermine si une personne a le droit de voter en France.

        Args:
            algo_input: Entrée contenant les attributs de la personne.

        Returns:
            AlgoResult avec True/False et la traçabilité complète.

        Raises:
            ValueError: Si l'âge est négatif.
        """
        nationalite = bool(algo_input.data["nationalite_francaise"])
        age = int(algo_input.data["age"])
        capacite = bool(algo_input.data["capacite_civique"])
        inscrit = bool(algo_input.data["inscrit_listes_electorales"])

        if age < 0:
            raise ValueError(f"L'âge doit être positif, reçu : {age}")

        type_election = algo_input.context.get("type_election", "nationale")

        if type_election == "municipale":
            citoyennete_ue = bool(algo_input.data.get("citoyennete_ue", False))
            domicile_france = bool(algo_input.data.get("domicile_france", False))
            # Art. 88-3 C° / L.O. 227-1 : citoyen UE résidant en France
            eligible_nationalite = nationalite or (citoyennete_ue and domicile_france)
        else:
            eligible_nationalite = nationalite
            citoyennete_ue = bool(algo_input.data.get("citoyennete_ue", False))
            domicile_france = bool(algo_input.data.get("domicile_france", False))

        peut_voter = eligible_nationalite and age >= 18 and capacite and inscrit

        return AlgoResult(
            value=peut_voter,
            algo_id=self.algo_id,
            regulation=self.regulation,
            inputs_snapshot=algo_input.data,
            metadata={
                "type_election": type_election,
                "conditions": {
                    "eligible_nationalite": eligible_nationalite,
                    "nationalite_francaise": nationalite,
                    "citoyennete_ue_avec_domicile_france": citoyennete_ue and domicile_france,
                    "age_suffisant": age >= 18,
                    "capacite_civique": capacite,
                    "inscrit_listes_electorales": inscrit,
                },
            },
        )