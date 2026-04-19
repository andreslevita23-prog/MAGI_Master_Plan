# Deployment

## Plataforma elegida

**Render** es la mejor opcion para el proyecto actual porque:

- la app ya corre como servidor Express
- no hace falta separar frontend y backend
- no requiere build complejo
- soporta custom domains y TLS gestionado
- usa `npm start` y `PORT` de forma natural

## Estado actual diagnosticado

La aplicacion corre localmente, pero el dominio publico no esta sirviendo la web.

La razon principal detectada en el repo es que existe una configuracion vieja de **Cloudflare Tunnel** en `config/cloudflared.yml` que apunta a:

- `prosperity.lat -> http://localhost:3000`

Eso no equivale a un despliegue publico persistente. Si no hay una maquina encendida con `cloudflared` corriendo y el servidor local activo, el dominio no puede servir la app.

Ademas, el repo no tenia configuracion de plataforma de hosting publica lista para deploy hasta esta fase.

## Render

### Configuracion preparada

- `render.yaml`
- `startCommand: npm start`
- `buildCommand: npm install`
- `healthCheckPath: /health`

### Pasos minimos

1. Entrar a Render.
2. Crear un nuevo **Web Service** desde el repo GitHub.
3. Usar la rama `chore/magi-recovery`.
4. Confirmar que Render genere una URL `*.onrender.com`.
5. Agregar `prosperity.lat` como custom domain.
6. Agregar `www.prosperity.lat` si se desea.
7. Configurar los DNS records con tu proveedor.
8. Verificar el dominio en Render.
9. Esperar emision automatica del certificado TLS.

## DNS recomendado

### Si usas Cloudflare DNS

- `CNAME` `@` -> `<tu-servicio>.onrender.com`
- `CNAME` `www` -> `<tu-servicio>.onrender.com`
- quitar `AAAA`
- dejar `DNS only` mientras Render verifica

### Si usas Namecheap u otro proveedor

- `A` `@` -> `216.24.57.1`
- `CNAME` `www` -> `<tu-servicio>.onrender.com`
- quitar `AAAA`

## Lo que queda manual

- crear el servicio en Render
- obtener la URL temporal real `*.onrender.com`
- agregar el custom domain en Render
- cambiar DNS en el proveedor del dominio
- verificar el dominio y esperar SSL
