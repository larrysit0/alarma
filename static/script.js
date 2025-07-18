document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const comunidadSeleccionada = urlParams.get('comunidad');

    if (!comunidadSeleccionada) {
        alert("❌ No se especificó la comunidad en la URL.");
        return;
    }

    let ubicacionesPredeterminadas = [];
    let ubicacionSeleccionada = null;
    let userData = null; // <-- NUEVA VARIABLE para guardar los datos del usuario

    const textarea = document.getElementById('descripcion');
    const boton = document.getElementById('btnEmergencia');
    const statusMsg = document.getElementById('statusMsg');
    const toggleRealTime = document.getElementById('toggleRealTime');

    // --- ⭐ CAMBIO AQUI: Obtener datos del usuario de Telegram WebApp ⭐ ---
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
        userData = window.Telegram.WebApp.initDataUnsafe.user;
        console.log("Datos del usuario de Telegram:", userData);
        if (userData && userData.first_name) {
            statusMsg.textContent = `👋 Hola ${userData.first_name} en ${comunidadSeleccionada.toUpperCase()}`;
        } else {
            statusMsg.textContent = `👥 Comunidad detectada: ${comunidadSeleccionada.toUpperCase()}`;
        }
    } else {
        console.warn("Telegram WebApp API no disponible o initDataUnsafe no cargado.");
        statusMsg.textContent = `👥 Comunidad detectada: ${comunidadSeleccionada.toUpperCase()}`;
    }
    // ----------------------------------------------------------------------

    // ... (el resto de tu código de carga de ubicaciones, validación de texto, etc., no cambia) ...
    cargarUbicaciones(comunidadSeleccionada);

    function cargarUbicaciones(comunidad) {
        fetch(`/api/ubicaciones/${comunidad}`)
            .then(res => {
                if (!res.ok) throw new Error(`Error al cargar ubicaciones: ${res.status}`);
                return res.json();
            })
            .then(data => {
                ubicacionesPredeterminadas = data;
                if (ubicacionesPredeterminadas.length > 0) {
                    ubicacionSeleccionada = ubicacionesPredeterminadas[0];
                    statusMsg.textContent = `📍 Usando ubicación predeterminada de ${ubicacionSeleccionada.nombre}`;
                } else {
                    statusMsg.textContent = "⚠️ No hay ubicaciones predeterminadas para esta comunidad.";
                }
            })
            .catch(error => {
                console.error("❌ Error:", error.message);
                statusMsg.textContent = "❌ No se pudieron cargar las ubicaciones.";
            });
    }

    textarea.addEventListener('input', () => {
        const texto = textarea.value.trim();
        if (texto.length >= 4 && texto.length <= 300) {
            boton.disabled = false;
            boton.classList.add('enabled');
            // Mantener el mensaje de bienvenida o ubicación si ya se estableció
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
        const descripcion = textarea.value.trim();

        if (!descripcion || !comunidadSeleccionada || !ubicacionSeleccionada) {
            alert("❌ Faltan datos necesarios");
            return;
        }
        
        // --- ⭐ CAMBIO AQUI: Validar que tenemos userData antes de enviar ⭐ ---
        if (!userData) {
            alert("❌ No se pudieron obtener los datos de tu usuario de Telegram. Intenta abrir la Web App de nuevo.");
            resetFormulario();
            return;
        }
        // ----------------------------------------------------------------------

        boton.disabled = true;
        boton.textContent = "Enviando...";
        statusMsg.textContent = "🔄 Enviando alerta...";

        if (toggleRealTime.checked && navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(pos => {
                enviarAlerta(descripcion, pos.coords.latitude, pos.coords.longitude, userData); // <-- PASA userData
            }, () => {
                alert("❌ No se pudo obtener ubicación en tiempo real.");
                resetFormulario();
            });
        } else {
            if (!ubicacionSeleccionada || !ubicacionSeleccionada.geolocalizacion) {
                alert("❌ No se ha seleccionado una ubicación válida.");
                resetFormulario();
                return;
            }
            const { lat, lon } = ubicacionSeleccionada.geolocalizacion;
            enviarAlerta(descripcion, lat, lon, userData); // <-- PASA userData
        }
    });

    // --- ⭐ CAMBIO AQUI: La función ahora acepta 'userData' ⭐ ---
    function enviarAlerta(descripcion, lat, lon, userData) {
        console.log("📤 Enviando comunidad:", comunidadSeleccionada);
        const direccion = ubicacionSeleccionada.direccion || "Dirección no disponible";
        fetch('/api/alert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tipo: "Alerta Roja Activada",
                descripcion,
                ubicacion: { lat, lon },
                direccion: direccion,
                comunidad: comunidadSeleccionada,
                user_telegram: { // <-- NUEVO: Datos del usuario de Telegram
                    id: userData.id,
                    first_name: userData.first_name,
                    last_name: userData.last_name || '', // Puede ser opcional
                    username: userData.username || ''    // Puede ser opcional
                }
            })
        })
        // ... (el resto del .then y .catch permanece igual) ...
            .then(res => res.json())
            .then(data => {
                alert(data.status || "✅ Alerta enviada correctamente.");
                resetFormulario();
            })
            .catch(err => {
                console.error("❌ Error al enviar alerta:", err);
                alert("❌ Error al enviar alerta.");
                resetFormulario();
            });
    }

    function resetFormulario() {
        boton.disabled = true;
        boton.textContent = "🚨 Enviar Alerta Roja";
        statusMsg.textContent = "⏳ Esperando acción del usuario...";
        textarea.value = "";
        boton.classList.remove('enabled');
        // Re-evaluar el mensaje de bienvenida si el usuario aún está presente
        if (userData && userData.first_name) {
            statusMsg.textContent = `👋 Hola ${userData.first_name} en ${comunidadSeleccionada.toUpperCase()}`;
        }
    }
});
