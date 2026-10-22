# Centro de Monitoreo GOZT

Panel independiente para comprobar disponibilidad HTTP de los sistemas. No modifica sistemas productivos ni sus bases de datos.

## Sistemas

- Sistema de Recepción — El Toro Reciclados
- Sistema de Inventario
- Localcito: desactivado hasta confirmar su URL actual
- Freddy Rojas: desactivado hasta recibir su URL

## Configuración

El workflow en `.github/workflows/monitor.yml` ejecuta comprobaciones programadas y publica el panel con GitHub Pages. Tras el primer workflow, revisar **Settings → Pages** y elegir **GitHub Actions** si se solicita.

Las alertas por correo son opcionales. Configurar en **Settings → Secrets and variables → Actions**: `SMTP_HOST`, `SMTP_PORT` (normalmente `587`), `SMTP_USER`, `SMTP_PASSWORD` y `ALERT_EMAIL`. No guardar contraseñas en archivos.

Las comprobaciones HTTP no garantizan que todas las funciones internas estén operativas. GitHub Actions puede retrasarse y está sujeto a los límites del plan de GitHub.