document.addEventListener('DOMContentLoaded', () => {
    const BACKEND_URL = "https://alarma-production.up.railway.app";
    console.log("✅ Script cargado. Backend URL:", BACKEND_URL);

    const urlParams = new URLSearchParams(window.location.search);
    const comunidadSeleccionada = urlParams.get('comunidad');

    if (!comunidadSeleccionada) {
        alert("❌ No se especificó la comunidad en la URL.");
        return;
    }
    console.log("✅ Comunidad seleccionada:", comunidadSeleccionada);

    let ubicacionesPredeterminadas = [];
    let ubicacionSeleccionada = null;
    let userData = null;

    const textarea = document.getElementById('descripcion');
    const boton = document.getElementById('btnEmergencia');
    const statusMsg = document.getElementById('statusMsg');
    const toggleRealTime = document.getElementById('toggleRealTime');

    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
        userData = window.Telegram.WebApp.initDataUnsafe.user;
        console.log("✅ Datos del usuario de Telegram cargados:", userData);
        if (userData && userData.first_name) {
            statusMsg.textContent = `👋 Hola ${userData.first_name} en ${comunidadSeleccionada.toUpperCase()}`;
        } else {
            statusMsg.textContent = `👥 Comunidad detectada: ${comunidadSeleccionada.toUpperCase()}`;
        }
    } else {
        console.warn("⚠️ Telegram WebApp API no disponible. Esto es normal fuera de Telegram.");
        statusMsg.textContent = `👥 Comunidad detectada: ${comunidadSeleccionada.toUpperCase()}`;
    }

    cargarUbicaciones(comunidadSeleccionada);

    function cargarUbicaciones(comunidad) {
        fetch(`${BACKEND_URL}/api/ubicaciones/${comunidad}`)
            .then(res => {
                if (!res.ok) throw new Error(`Error al cargar ubicaciones: ${res.status}`);
                return res.json();
            })
            .then(data => {
                ubicacionesPredeterminadas = data;
                if (ubicacionesPredeterminadas.length > 0) {
                    ubicacionSeleccionada = ubicacionesPredeterminadas[0];
                    statusMsg.textContent = `📍 Usando ubicación predeterminada de ${ubicacionSeleccionada.nombre}`;
                    console.log("✅ Ubicaciones cargadas correctamente.");
                } else {
                    statusMsg.textContent = "⚠️ No hay ubicaciones predeterminadas para esta comunidad.";
                    console.warn("⚠️ No hay ubicaciones predeterminadas.");
                }
            })
            .catch(error => {
                console.error("❌ Error en cargarUbicaciones:", error.message);
                statusMsg.textContent = "❌ No se pudieron cargar las ubicaciones.";
            });
    }

    textarea.addEventListener('input', () => {
        const texto = textarea.value.trim();
        if (texto.length >= 4 && texto.length <= 300) {
            boton.disabled = false;
            boton.classList.add('enabled');
            if (!statusMsg.textContent.startsWith("👋 Hola")) {
                statusMsg.textContent = "✅ Listo para enviar";
            }
        } else {
            boton.disabled = true;
            boton.classList.remove('enabled');
            statusMsg.textContent = "⏳ Esperando acción del usuario...";
        }
    });

    toggleRealTime.addEventListener('change', () => {
        if (toggleRealTime.checked) {
            statusMsg.textContent = "📍 Usando ubicación en tiempo real";
        } else if (ubicacionSeleccionada) {
            statusMsg.textContent = `📍 Usando ubicación predeterminada de ${ubicacionSeleccionada.nombre}`;
        }
    });

    boton.addEventListener('click', () => {
        console.log("➡️ Evento 'click' en el botón detectado.");
        const descripcion = textarea.value.trim();

        if (!descripcion || !comunidadSeleccionada || !ubicacionSeleccionada) {
            console.error("❌ Validación fallida: faltan datos necesarios.");
            alert("❌ Faltan datos necesarios");
            return;
        }
        
        if (!userData) {
            console.error("❌ Validación fallida: userData no disponible.");
            alert("❌ No se pudieron obtener los datos de tu usuario de Telegram. Intenta abrir la Web App de nuevo.");
            resetFormulario();
            return;
        }

        boton.disabled = true;
        boton.textContent = "Enviando...";
        statusMsg.textContent = "🔄 Enviando alerta...";

        if (toggleRealTime.checked && navigator.geolocation) {
            console.log("➡️ Solicitando ubicación en tiempo real...");
            navigator.geolocation.getCurrentPosition(pos => {
                console.log("✅ Ubicación obtenida. Llamando a enviarAlerta.");
                enviarAlerta(descripcion, pos.coords.latitude, pos.coords.longitude, userData);
            }, () => {
                console.error("❌ Error al obtener ubicación en tiempo real.");
                alert("❌ No se pudo obtener ubicación en tiempo real.");
                resetFormulario();
            });
        } else {
            if (!ubicacionSeleccionada || !ubicacionSeleccionada.geolocalizacion) {
                console.error("❌ Validación fallida: ubicación no válida.");
                alert("❌ No se ha seleccionado una ubicación válida.");
                resetFormulario();
                return;
            }
            console.log("➡️ Usando ubicación predeterminada. Llamando a enviarAlerta.");
            const { lat, lon } = ubicacionSeleccionada.geolocalizacion;
            enviarAlerta(descripcion, lat, lon, userData);
        }
    });

    function enviarAlerta(descripcion, lat, lon, userData) {
        console.log("➡️ ENVIAR ALERTA: La función ha sido llamada.");
        console.log("📤 Datos a enviar:", { descripcion, lat, lon, userData });
        
        const direccion = ubicacionSeleccionada.direccion || "Dirección no disponible";

        fetch(`${BACKEND_URL}/api/alert`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tipo: "Alerta Roja Activada",
                descripcion,
                ubicacion: { lat, lon },
                direccion: direccion,
                comunidad: comunidadSeleccionada,
                user_telegram: {
                    id: userData.id,
                    first_name: userData.first_name,
                    last_name: userData.last_name || '',
                    username: userData.username || ''
                }
            })
        })
            .then(res => {
                console.log("✅ Respuesta del servidor recibida (Headers):", res.status);
                if (!res.ok) {
                    throw new Error(`Error del servidor: ${res.status} ${res.statusText}`);
                }
                return res.json();
            })
            .then(data => {
                console.log("✅ Respuesta del servidor (JSON):", data);
                alert(data.status || "✅ Alerta enviada correctamente.");
                resetFormulario();
            })
            .catch(err => {
                console.error("❌ Error en la llamada fetch:", err);
                alert("❌ Error al enviar alerta. Consulta la consola para más detalles.");
                resetFormulario();
            });
    }

    function resetFormulario() {
        boton.disabled = true;
        boton.textContent = "🚨 Enviar Alerta Roja";
        statusMsg.textContent = "⏳ Esperando acción del usuario...";
        textarea.value = "";
        boton.classList.remove('enabled');
        if (userData && userData.first_name) {
            statusMsg.textContent = `👋 Hola ${userData.first_name} en ${comunidadSeleccionada.toUpperCase()}`;
        }
    }
});
