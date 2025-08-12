document.addEventListener('DOMContentLoaded', () => {
    // URL base de tu backend. Asegúrate de que esta URL sea correcta.
    const BACKEND_URL = "https://alarma-production.up.railway.app";
    console.log("✅ Script cargado. Backend URL:", BACKEND_URL);

    // Variables globales para almacenar los datos del usuario, chat y comunidad.
    let userData = null;
    let chatId = null;
    let comunidadSeleccionada = null; // Esta variable se llenará dinámicamente
    let comunidadMiembros = [];
    let currentUserMemberData = null;

    // Elementos del DOM (Interfaz de Usuario)
    const textarea = document.getElementById('descripcion');
    const boton = document.getElementById('btnEmergencia');
    const statusMsg = document.getElementById('statusMsg');
    const toggleRealTime = document.getElementById('toggleRealTime');

    // --- LÓGICA PRINCIPAL: OBTENER DATOS DE LA WEB APP ---
    // Verificamos si la aplicación se está ejecutando dentro de Telegram.
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
        const webAppData = window.Telegram.WebApp.initDataUnsafe;
        
        // Obtenemos los datos del usuario y del chat desde la API de Telegram.
        userData = webAppData.user;
        chatId = webAppData.chat?.id; // Usamos el operador ?. para evitar errores si 'chat' es nulo

        if (!chatId) {
            console.error("❌ No se encontró el chat_id en los datos de la Web App.");
            alert("❌ Error: No se pudo determinar el chat. Por favor, contacta a un administrador.");
            boton.disabled = true;
            boton.textContent = "❌ Error";
            return;
        }

        console.log("✅ Datos de usuario de Telegram cargados:", userData);
        console.log("✅ Chat ID detectado:", chatId);
        
        // Intentamos cargar los datos de la comunidad usando el chat_id.
        // Esto llamará al nuevo endpoint /api/comunidad_por_chat/<chat_id>
        cargarDatosComunidad(chatId);

        // Actualizamos el mensaje de estado inicial en la interfaz.
        if (userData && userData.first_name) {
            statusMsg.textContent = `👋 Hola ${userData.first_name}, presiona para enviar una alerta.`;
        } else {
            statusMsg.textContent = "👥 Grupo detectado.";
        }
    } else {
        console.error("❌ La Web App no se ha cargado en Telegram o no hay datos.");
        alert("❌ Este botón solo funciona dentro de Telegram.");
        boton.disabled = true;
        boton.textContent = "❌ Error (Fuera de Telegram)";
        return;
    }

    // --- FUNCIONES ASÍNCRONAS ---

    async function cargarDatosComunidad(chatId) {
        try {
            // Llama al nuevo endpoint en tu servidor para obtener la comunidad por chat_id
            const res = await fetch(`${BACKEND_URL}/api/comunidad_por_chat/${chatId}`);
            if (!res.ok) throw new Error(`Error al cargar datos de la comunidad: ${res.status}`);
            
            const comunidadData = await res.json();
            comunidadSeleccionada = comunidadData.comunidad; // El servidor devuelve el nombre de la comunidad
            comunidadMiembros = comunidadData.miembros || [];
            
            console.log("✅ Datos de la comunidad cargados:", comunidadData);
            
            if (userData && userData.id) {
                currentUserMemberData = comunidadMiembros.find(m => String(m.telegram_id) === String(userData.id));
                if (currentUserMemberData) {
                    console.log("✅ Datos registrados del usuario actual encontrados:", currentUserMemberData);
                } else {
                    console.warn("⚠️ Usuario actual no encontrado en la lista de miembros de la comunidad.");
                }
            }
        } catch (error) {
            console.error("❌ Error en cargarDatosComunidad:", error.message);
            statusMsg.textContent = "❌ No se pudieron cargar los datos de la comunidad.";
            boton.disabled = true;
            boton.textContent = "❌ Error";
            boton.classList.remove('enabled');
            return;
        }
        updateStatusMessageBasedOnToggle();
        // Habilitar el botón si todo se cargó correctamente y el texto es válido
        const texto = textarea.value.trim();
        const isValid = texto.length >= 4 && texto.length <= 300 && comunidadSeleccionada;
        boton.disabled = !isValid;
        boton.classList.toggle('enabled', isValid);
    }

    // --- MANEJO DE LA INTERFAZ DE USUARIO Y EVENTOS ---

    function updateStatusMessageBasedOnToggle() {
        if (toggleRealTime.checked) {
            statusMsg.textContent = "📍 Usando ubicación en tiempo real";
        } else if (currentUserMemberData && currentUserMemberData.direccion) {
            statusMsg.textContent = `📍 Tu dirección registrada: ${currentUserMemberData.direccion}`;
        } else {
            statusMsg.textContent = "⚠️ Ubicación no disponible. Por favor, activa GPS.";
        }
    }

    textarea.addEventListener('input', () => {
        const texto = textarea.value.trim();
        // La validación ahora también incluye que la comunidad haya sido cargada
        const isValid = texto.length >= 4 && texto.length <= 300 && comunidadSeleccionada;
        
        boton.disabled = !isValid;
        boton.classList.toggle('enabled', isValid);
        statusMsg.textContent = isValid ? "✅ Listo para enviar" : "⏳ Esperando acción del usuario...";
        if (isValid) {
            updateStatusMessageBasedOnToggle();
        }
    });

    toggleRealTime.addEventListener('change', () => {
        updateStatusMessageBasedOnToggle();
    });

    boton.addEventListener('click', () => {
        console.log("➡️ Evento 'click' en el botón detectado.");
        const descripcion = textarea.value.trim();

        if (!descripcion || !comunidadSeleccionada) {
            console.error("❌ Validación fallida: faltan datos necesarios.");
            alert("❌ Faltan datos necesarios");
            return;
        }
        
        boton.disabled = true;
        boton.textContent = "Enviando...";
        statusMsg.textContent = "🔄 Enviando alerta...";

        let latEnvio = null;
        let lonEnvio = null;
        let direccionEnvio = "Dirección no disponible";

        if (currentUserMemberData && currentUserMemberData.direccion) {
            direccionEnvio = currentUserMemberData.direccion;
        }

        if (toggleRealTime.checked && navigator.geolocation) {
            console.log("➡️ Solicitando ubicación en tiempo real...");
            navigator.geolocation.getCurrentPosition(pos => {
                latEnvio = pos.coords.latitude;
                lonEnvio = pos.coords.longitude;
                console.log("✅ Ubicación obtenida (tiempo real).");
                enviarAlerta(descripcion, latEnvio, lonEnvio, direccionEnvio, userData);
            }, () => {
                console.error("❌ Error al obtener ubicación en tiempo real. Usando ubicación registrada si existe.");
                alert("❌ No se pudo obtener ubicación en tiempo real. Usando tu ubicación registrada.");
                handleFallbackLocation(descripcion, userData, direccionEnvio);
            });
        } else {
            handleFallbackLocation(descripcion, userData, direccionEnvio);
        }
    });

    function handleFallbackLocation(descripcion, userData, direccionFija) {
        let latEnvio = null;
        let lonEnvio = null;
        let direccionEnvio = direccionFija;

        if (currentUserMemberData && currentUserMemberData.geolocalizacion) {
            latEnvio = currentUserMemberData.geolocalizacion.lat;
            lonEnvio = currentUserMemberData.geolocalizacion.lon;
            direccionEnvio = currentUserMemberData.geolocalizacion.direccion || direccionFija;
            console.log("➡️ Fallback: Usando ubicación registrada del miembro.");
            enviarAlerta(descripcion, latEnvio, lonEnvio, direccionEnvio, userData);
        } else {
            console.error("❌ Fallback: No se encontró ubicación válida.");
            enviarAlerta(descripcion, latEnvio, lonEnvio, direccionEnvio, userData);
        }
    }

    function enviarAlerta(descripcion, lat, lon, direccion, userData) {
        console.log("➡️ ENVIAR ALERTA: La función ha sido llamada.");
        
        const userTelegramData = userData ? {
            id: userData.id,
            first_name: userData.first_name,
            last_name: userData.last_name || '',
            username: userData.username || ''
        } : {
            id: 'Desconocido',
            first_name: 'Anónimo',
            last_name: '',
            username: ''
        };

        console.log("📤 Datos de alerta a enviar:", {
            tipo: "Alerta Roja Activada",
            descripcion,
            ubicacion: { lat, lon },
            direccion,
            chat_id: chatId, // Se envía el chat_id
            user_telegram: userTelegramData
        });

        fetch(`${BACKEND_URL}/api/alert`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tipo: "Alerta Roja Activada",
                descripcion,
                ubicacion: { lat, lon },
                direccion: direccion,
                chat_id: chatId, // ¡Corrección: Ahora enviamos el chat_id!
                user_telegram: userTelegramData
            })
        })
        .then(res => {
            console.log("✅ Respuesta del servidor recibida:", res.status);
            if (!res.ok) {
                throw new Error(`Error del servidor: ${res.status} ${res.statusText}`);
            }
            return res.json();
        })
        .then(data => {
            console.log("✅ Respuesta del servidor (JSON):", data);
            alert(data.status || "✅ Alerta enviada correctamente.");
            // También puedes cerrar la Web App automáticamente después de enviar la alerta
            if (window.Telegram && window.Telegram.WebApp) {
                 window.Telegram.WebApp.close();
            }
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
        textarea.value = "";
        boton.classList.remove('enabled');
        updateStatusMessageBasedOnToggle();
    }
});
