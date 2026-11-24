---
okf_version: "0.3"
title: Base de connaissance pole Dixit — PoC OKF
description: Connaissances commerciales du pole Dixit (clients anonymises, deals, signaux faibles, playbooks) au format Open Knowledge Format v0.3, consommees par les agents LibreChat.
license: Interne — PoC seminaire
---

# Pole Dixit — Base de connaissance OKF

## Contenu

- [Clients](clients/index.md) — comptes anonymises suivis en developpement commercial
- [Deals](deals/index.md) — opportunites en cours, liees aux clients
- [Signaux](signals/index.md) — signaux faibles issus du canal GChat et des mails exportes (anonymises)
- [Playbooks](playbooks/index.md) — regles d'action du coaching commercial

## Regles de consommation (agents)

1. Lire cet index, puis suivre les liens entre concepts.
2. Verifier `status` et `stale_after` dans le frontmatter avant toute utilisation ; signaler si perime.
3. Citer les sources (`sources` du frontmatter + section `# Citations` du corps).
4. Ne jamais inventer de fait : si l'info n'est pas dans le bundle, le dire.
