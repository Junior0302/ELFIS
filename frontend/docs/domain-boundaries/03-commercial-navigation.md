# 03 — Navigation Commercial



Source : `sales/salesNavModel.ts` (`salesNavCategories`) + `SalesProductNav` (accordion = Finance).



Voir aussi [10-commercial-nav-parity.md](./10-commercial-nav-parity.md).



## Structure livrée



| Section | Entrées | Routes |

|---------|---------|--------|

| Principal | Tableau de bord | `/sales` |

| Prospection | Prospects, Entreprises, Contacts, Import | `/sales/leads`, `/companies`, `/contacts`, `/import` |

| Pipeline | Vue d’ensemble, Propositions | `/sales/pipeline`, `/proposals` |

| Activités | Vue d’ensemble, Calendrier, Tâches, Journal | `/sales/activities`, `/calendar`, `/tasks`, `/journal` |

| Reporting | Vue d’ensemble, Performances | `/sales/reports`, `/intelligence` |

| Clients | Entreprises, Contacts, Relations (ELFIS) | `/sales/companies`, `/contacts`, `/platform/relations` |

| Paramètres | Général | `/sales/settings` |



## Hors menu (routes conservées)



- `/sales/team`, `/sales/collab/views`, `/sales/duplicates` — deep link, pas doublon Organisation.



## Interdit (menu permanent)



Organisation, Members, paramètres ELFIS, documents / communications plateforme.



Relations = **lien contextuel** sous Clients (badge ELFIS), pas un second CRM.

