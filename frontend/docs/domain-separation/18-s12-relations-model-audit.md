# 18 — S1.2 Relations model audit

| Entité | Table | Modèle | API | Org | PK | Champs communs | Spécifique | Frontend |
|--------|-------|--------|-----|-----|----|----------------|------------|----------|
| Customer | `customers` | `models_saas.Customer` | `/billing/customers` | oui | id | name, email, phone, address, vat | — | `listCustomers` |
| Contact | `contacts` | `models_saas.Contact` | `/contacts*` | oui | id | company, names, email, phone, address, siren/siret/vat | contact_type, payment_terms, IBAN | `listContacts` |
| SalesCompany | `sales_companies` | `sales_crm.SalesCompany` | `/sales/companies` | oui | id | name, email, phone, address, siret, vat | owner, linked_customer/contact | `listSalesCompanies` |
| SalesPerson | `sales_people` | `SalesPerson` | `/sales/contacts` | oui | id | names, email, phone | company_id, job | Sales contacts |
| Organization | `organizations` | `Organization` | `/org/*` | — | id | legal identity tenant | — | Organisation page |
| Company (filiale) | `companies` | `Company` | org admin | oui | id | name | parent | rare |
| Member | `organization_members` | `OrganizationMember` | `/org/.../members` | oui | id | user link | role | AdminEquipe |
| User | `users` | `User` | auth | — | id | email, name | — | compte |

## Sources de vérité actuelles (pré-Party)

- Facturation clients → `customers`
- Fournisseurs / prospects contacts → `contacts`
- CRM comptes → `sales_companies`
- Pas de table `parties` unique

## Risque

Doublons cross-table (même email/SIREN dans customer + contact + sales_company).

## Stratégie S1.2

Adapters lecture → `SharedRelation` sans fusion physique.
