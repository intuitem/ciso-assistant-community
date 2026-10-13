# Plan de test UI : boutons visibles par l'analyste mais refusés par le back

Branche : `fix/analyst-ui-permission-gating`. Version de référence : `main`.

> Ce fichier sert seulement au test. Ne pas le committer.

## 0. Préparation (une seule fois)

### Comptes

En tant qu'admin, créer un domaine **« Domaine A »** (les groupes de rôles du domaine sont créés automatiquement), puis 3 utilisateurs :

| Compte | Groupe |
|---|---|
| `admin@…` | admin existant |
| `dm@…` | « Domaine A - Domain Manager » |
| `analyste@…` | « Domaine A - Analyst » |

Utiliser une fenêtre de navigation privée par compte pour ne pas mélanger les sessions.

### Jeu de données (créé en admin)

- **Feature flags** à activer dans Paramètres : workflows, campagnes / TPRM, quick forms, journeys, security advisories (si disponibles).
- **Librairie avec workflows :** charger une librairie qui contient des workflows (pour le bouton « Instantiate workflow »).
- **Librairie à mettre à jour :** une librairie chargée qui a une mise à jour disponible (icône ⬆ dans `/libraries`). Le plus simple est de charger une ancienne version d'une librairie, puis de déposer la nouvelle version.
- **Workflow :** dans Domaine A, créer un workflow publié avec au moins 1 trigger (de préférence un webhook), et archiver une ancienne version.
- **Campagne :** dans Domaine A, une campagne en brouillon avec au moins une cible.
- **Entity assessment :** dans Domaine A, une entity assessment liée à un audit (`compliance_assessment`).
- **Reference control :** une reference control liée à au moins une applied control de Domaine A dont la catégorie ou la fonction CSF diffère.
- **Task node :** un task node de Domaine A qui a une preuve « legacy » (preuve rattachée directement au node).
- **Quick form :** chargé depuis une librairie.
- **Journey :** appliqué, avec une version plus récente de sa librairie stockée.
- **Terminologies et entités :** une terminologie et une entité existantes (celles par défaut suffisent).

### Lancer l'appli

Lancer l'appli une fois sur `main` (passe AVANT), puis une fois sur la branche (passe APRÈS) :

```bash
git checkout main
```

```bash
git checkout fix/analyst-ui-permission-gating
```

Redémarrer le back à chaque changement de branche : il y a des modifications dans `backend/core/views.py`.

Ouvrir l'onglet **Réseau** des devtools pendant les tests AVANT pour voir les 403.

---

## 1. Cas à tester avec le compte **analyste**

Légende :
- **AVANT** = comportement sur `main` (le bug).
- **APRÈS** = comportement attendu sur la branche.

### A. Workflows

| # | Où | Action | AVANT | APRÈS |
|---|---|---|---|---|
| A1 | `/workflows` → ouvrir le workflow (version publiée) | Regarder l'en-tête | Interrupteur on/off et champ « timeout » affichés | Absents |
| A2 | Même page | Déplacer un nœud, cliquer sur un nœud | Le canvas est éditable, l'inspecteur s'ouvre ; la sauvegarde ou la publication renvoie 403 | Canvas en lecture seule (pas de drag, pas d'inspecteur), pas de bouton Publish |
| A3 | Même page | Bouton « Execute workflow » et sa flèche ▾ | Visible ; clic → 403 | Absent |
| A4 | Panneau **Versions** | « Restore as draft » sur une version archivée | Visible ; clic → 403 | Absent |
| A5 | Panneau **Triggers** | Interrupteur du trigger et icône 🔄 (rotate secret) | Actifs ; clic → 403 | Interrupteur grisé, icône absente |
| A6 | Panneau **Runs** | « Replay » sur un run | Visible | **Toujours visible** (animation locale sans appel au back) |
| A7 | `/workflows` liste → clic droit sur une ligne | « Disable workflow » | Visible ; clic → toast d'erreur | Absent |

### B. Librairies et Library builder

| # | Où | Action | AVANT | APRÈS |
|---|---|---|---|---|
| B1 | Menu latéral | Entrée « Library builder » | Visible | Absente |
| B2 | `/quick-forms` | Bouton « Library builder » dans le bandeau d'info | Visible | Absent (le texte du bandeau reste) |
| B3 | `/libraries` | Icône ⬆ « Update this library » | Visible ; clic → 403 | Absente |
| B4 | Page d'une librairie chargée ou stockée qui contient des workflows | « Instantiate workflow » | Visible ; validation → 403 | Absent (« Preview » reste) |
| B5 | Page d'un journey | « Upgrade available » (quand la librairie stockée est plus récente) | Visible ; clic → 403 | Absent |

### C. Sécurité (sec intel)

| # | Où | Action | AVANT | APRÈS |
|---|---|---|---|---|
| C1 | `/security-advisories` | Boutons 🇺🇸 Sync KEV et 🇪🇺 Sync EUVD | Visibles ; confirmation → 403 | Absents |
| C2 | `/cwes` | Bouton « Sync CWE catalog » | Visible ; clic → 403 | Absent |

### D. Pages de détail

| # | Où | Action | AVANT | APRÈS |
|---|---|---|---|---|
| D1 | `/campaigns/<id>` (brouillon avec cibles) | « Start campaign » | Visible ; confirmation → 403 | Absent |
| D2 | `/entity-assessments/<id>` | « New revision » | Visible ; clic → 403 | Absent (« Export » reste) |
| D3 | `/terminologies/<id>` | Bouton « Edit » | Visible ; enregistrer → 403 | Absent |
| D4 | `/quick-forms/<id>` → « Preview » | Ouvrir la prévisualisation | La page plante (403 au chargement) | **La page fonctionne** (correction côté back) |
| D5 | `/reference-controls/<id>` | « Sync to applied controls » → confirmer | Bouton visible ; confirmation → 403 | **Fonctionne** : les applied controls de Domaine A prennent la catégorie et la fonction CSF de la reference control |
| D6 | `/task-nodes/<id>` → bloc « preuves legacy » | Icônes ↗ (move) et ➖ (remove) | Visibles ; clic → 403 | **Fonctionnent** : la preuve disparaît du node (↗ la déplace vers le template) |

### E. Divers

| # | Où | Action | AVANT | APRÈS |
|---|---|---|---|---|
| E1 | Menu utilisateur (bas de la sidebar) | « Get started » | Visible ; « Load demo data » échoue | Absent |
| E2 | `/entities/<id>` d'une entité **d'un autre domaine** (lecture seule) | Bouton « Edit » | Visible ; enregistrer → 403 | Absent. Sur une entité de Domaine A, il reste visible. |

## 2. Cas à tester avec le compte **domain manager** (Domaine A)

Vérifier qu'on n'a rien retiré à tort, puis le seul correctif qui le concerne.

| # | Où | Attendu APRÈS |
|---|---|---|
| M1 | `/folders` | Le bouton « Import domain » (📥) est **absent** (il faut `add_folder` sur Global). AVANT : visible, puis 403 `userDoesNotHavePermissionToImportDomain`. |
| M2 | Workflow de Domaine A | Canvas éditable, Execute, Restore, triggers : **tout est présent** et fonctionne |
| M3 | Clic droit sur un workflow | « Disable workflow » est présent et fonctionne |
| M4 | Campagne de Domaine A | « Start campaign » est présent |
| M5 | Entity assessment | « New revision » est présent |
| M6 | Librairie avec workflows | « Instantiate workflow » est présent ; le sélecteur ne propose que Domaine A |
| M7 | Library builder, Sync KEV/CWE, Update library | Absents (réservés à l'admin) |

## 3. Non-régression avec le compte **admin**

Tous les boutons cités plus haut doivent rester **visibles et fonctionner** :
- Library builder (menu et bandeau quick forms) ;
- Update library ;
- Sync KEV / EUVD / CWE ;
- Get started ;
- Edit d'une terminologie ;
- Import domain ;
- Upgrade journey ;
- éditeur de workflow complet.

## 4. Tests automatiques (back)

```bash
cd backend && .venv/bin/python -m pytest core/tests/test_analyst_action_permissions.py -q
```

- Sur la branche : 5 tests passent.
- Sur `main` : les 4 tests « analyste » échouent (403). Le test « reader » passe dans les deux cas : il vérifie qu'un lecteur ne peut pas retirer de preuve.

## 5. Récap des fichiers modifiés

**Back.** `backend/core/views.py` : ajout de `permission_overrides` sur trois actions.
- `QuickFormViewSet.preview` → `view_quickform`.
- `ReferenceControlViewSet.sync_applied_controls` → `view_referencecontrol`. Les écritures restent limitées aux applied controls que l'utilisateur peut modifier.
- `TaskNodeViewSet.remove_evidence` → `change_tasknode`. Pour un « move », `change_tasktemplate` est aussi vérifié.

**Front.**
- **Workflows :** `+page.svelte`, `WorkflowCanvas.svelte`, `TriggersPanel.svelte` et `ContextMenu/workflows/ToggleActive.svelte`.
- **Librairies :** `Libraries/InstantiateWorkflows.svelte` et `ModelTable/field/LibraryActions.svelte`.
- **Menu et liste :** `navData.ts` (community et enterprise), `SideBarFooter.svelte` et `[model=urlmodel]/+page.svelte` (sync KEV/EUVD/CWE, lien vers le builder, import de domaine).
- **Pages de détail :** `DetailView.svelte` (Edit des terminologies et entités), et les pages `campaigns`, `entity-assessments`, `journeys`, `reference-controls` et `task-nodes`.
