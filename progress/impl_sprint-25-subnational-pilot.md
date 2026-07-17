# Sprint 25 - Subnational Pilot

## Intento 1

Resultado: OK

- El loader live del dashboard consulta GEE para paises habilitados y regiones piloto habilitadas por catalogo.
- El panel subnacional consume snapshots del piloto; si falta o no es concluyente, muestra `unknown`/`No data` sin heredar el score nacional.
- La UI conserva el selector/panel de region y muestra parent, nivel, fuente de geometria, ranking numerico y nota de cobertura nacional para paises sin piloto.
- Tests enfocados y suite completa pasan.
