from __future__ import annotations

import json
from pathlib import Path
import regalgo

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

    def compute(self, algo_input: regalgo.AlgoInput) -> regalgo.AlgoResult:
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

        return regalgo.AlgoResult(
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