# Proposition de publication simplifiée — 27 septembre 2026

Cette proposition répond à la demande d'Arthur de récupérer les contenus des cinq routines et de simplifier la mise à jour du site. Elle n'active pas à elle seule une migration et ne vaut pas publication des découvertes en attente.

## Principe

Conserver GitHub Pages, le dépôt et les dix filtres généraux. Donner à chaque axe de recherche son propre fichier JSON : concours, commandes, résidences, institutions et mécénat. Chaque routine ne modifie que son fichier, via une branche temporaire et une PR vers main. Le site réunit ces cinq fichiers. La validation porte sur la syntaxe JSON, les champs affichés, les identités et les doublons. Aucun service supplémentaire ni secret dans le site.

## Migration

1. Sauvegarder le dataset publié actuel et exporter séparément les contenus récupérables des routines. Distinguer texte présent, référence sans texte, recherche incomplète et intégration déjà vérifiée.
2. Répartir les seules fiches déjà publiées sans supprimer ni changer leurs champs. Vérifier que leur réunion reproduit exactement les données initiales.
3. Tester le chargement des cinq fichiers, le rendu, les filtres, le comportement réseau en erreur et les mises à jour. Garder un repli explicite sur les données historiques pendant la transition.
4. Fusionner la migration uniquement après ces tests. Adapter ensuite les cinq routines, sans en créer une sixième et sans effacer leur contenu en attente avant conservation vérifiée.
5. Intégrer les découvertes complètes séparément, après vérification de leurs sources et des éventuels blocages applicables. Ne pas transformer une référence incomplète en fiche inventée.

## Réussite observable

Une branche créée, un test local ou une PR ouverte ne sont pas une publication. Vérifier les données sur main, le déploiement associé et, séparément, les données réellement servies. Ne pas réécrire des données identiques pour provoquer un déploiement.

## Limites

Séparer les fichiers réduit les conflits entre axes mais ne répare pas un refus du connecteur. Un refus réel exige sa résolution légitime : ne pas le rejouer par un autre outil, compte ou chemin. La proposition ne change aucune permission ni protection de dépôt et ne publie aucun contenu précédemment refusé.
