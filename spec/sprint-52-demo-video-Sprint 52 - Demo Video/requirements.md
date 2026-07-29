# sprint-52-demo-video · Guion y grabación de la demo final — Requisitos

- name: `Sprint 52 - Demo Video` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-29T23:26:00.764Z

## Contexto

Preparar una demostración grabable de máximo tres minutos que muestre el recorrido diferencial de Mwangaza con claims verificables y un fallback estable.

## Requisitos funcionales

R1. Existe `docs/demo-script.md` con narración literal, acciones en pantalla y tiempos que suman como máximo 180 segundos.
R2. El guion recorre `/landing`, `/overview?layer=episodes` y un detalle ADM1 activo, usando uno de los escenarios finales versionados.
R3. El vídeo explica de forma directa qué áreas tienen un episodio activo y qué probabilidad existe de que continúe a 30, 60, 90 o 180 días.
R4. La narración diferencia observación satelital, referencia histórica y predicción ML experimental, sin presentar el backtest como impacto observado ni certeza operativa.
R5. El guion no depende de Reports, Admin, PDF ni notificaciones, superficies retiradas del recorrido final.
R6. La preparación y el fallback evitan esperas visibles y permiten completar la grabación con las capturas finales si falla una consulta.
R7. La grabación no muestra claves, correos privados, consola, variables de entorno ni contenido ajeno al producto.
R8. El documento incluye checklist de grabación, subtítulos y verificación del archivo exportado desde una sesión no autenticada cuando la plataforma lo requiera.

## Restricciones

- **error_states:** fallback con capturas finales si falla la consulta o la navegación
- **auth_secrets:** no mostrar consola, variables, credenciales ni información privada
- **rollback_compat:** solo documentación y preparación aditiva de la demo
