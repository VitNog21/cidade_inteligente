<template>
  <div id="app-container">
    <header class="app-header">
      <div class="logo">
        <i class="ph-bold ph-buildings"></i>
        <h1>Smart City Dashboard</h1>
      </div>
      <div class="status-indicator">
        <span>Status da Conexão:</span>
        <span class="dot" :class="connectionStatus"></span>
        <span>{{ connectionStatusText }}</span>
      </div>
    </header>
    
    <main class="main-content">
      <div v-if="isLoading" class="full-page-feedback">
        <i class="ph-bold ph-spinner-gap"></i>
        <h2>Carregando Dispositivos...</h2>
      </div>

      <div v-else-if="!devices.length" class="full-page-feedback">
        <i class="ph-bold ph-wifi-slash"></i>
        <h2>Nenhum dispositivo encontrado</h2>
        <p>Aguardando conexão dos dispositivos ou da API...</p>
      </div>

      <div v-else class="device-grid">
        <div v-for="device in devices" :key="device.id" class="device-card" :class="{ 'is-on': isDeviceOn(device) }">
          <div class="card-header">
            <i class="device-icon" :class="getDeviceIcon(device.type)"></i>
            <span class="device-id">{{ device.id }}</span>
          </div>
          <div class="card-body">
            <span class="device-status">{{ device.status }}</span>
          </div>
          <div class="card-footer" v-if="device.type === 'LAMP'">
            <button @click="sendCommand(device.id, 'TURN_ON')" class="btn-on">
              <i class="ph-bold ph-power"></i> Ligar
            </button>
            <button @click="sendCommand(device.id, 'TURN_OFF')" class="btn-off">
              <i class="ph-bold ph-power"></i> Desligar
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'App',
  data() {
    return {
      devices: [],
      isLoading: true, // Novo estado para controlar o carregamento inicial
      intervalId: null,
      connectionStatus: 'connecting', // connecting, online, offline
    };
  },
  computed: {
    connectionStatusText() {
      const statusMap = {
        online: 'Online',
        offline: 'Offline',
        connecting: 'Conectando...',
      };
      return statusMap[this.connectionStatus];
    }
  },
  methods: {
    async fetchDevices() {
      try {
        const response = await axios.get('http://localhost:8000/api/devices');
        this.devices = response.data.devices || [];
        this.connectionStatus = 'online';
      } catch (error) {
        console.error("Erro ao buscar dispositivos:", error);
        this.devices = []; // Limpa os dispositivos em caso de erro
        this.connectionStatus = 'offline';
      } finally {
        // Garante que o estado de "carregando" seja desativado após a primeira tentativa
        if (this.isLoading) {
          this.isLoading = false;
        }
      }
    },
    async sendCommand(deviceId, action) {
      try {
        await axios.post(`http://localhost:8000/api/devices/${deviceId}/command`, { action });
        setTimeout(this.fetchDevices, 300);
      } catch (error) {
        console.error(`Erro ao enviar comando para ${deviceId}:`, error);
        this.connectionStatus = 'offline';
      }
    },
    getDeviceIcon(type) {
      const icons = {
        LAMP: 'ph-bold ph-lightbulb',
        TEMP_SENSOR: 'ph-bold ph-thermometer-simple',
      };
      return icons[type] || 'ph-bold ph-question';
    },
    isDeviceOn(device) {
        return device.type === 'LAMP' && device.status === 'ON';
    }
  },
  mounted() {
    this.fetchDevices();
    this.intervalId = setInterval(this.fetchDevices, 5000);
  },
  beforeUnmount() {
    clearInterval(this.intervalId);
  }
};
</script>

<style>
/* O CSS da resposta anterior continua o mesmo. Cole ele aqui. */
:root {
  --bg-color: #1a1b26;
  --surface-color: #24283b;
  --card-color: #2a2e42;
  --primary-text: #c0caf5;
  --secondary-text: #a9b1d6;
  --accent-color: #7aa2f7;
  --green-status: #9ece6a;
  --red-status: #f7768e;
  --orange-status: #ff9e64;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Roboto', sans-serif;
  background-color: var(--bg-color);
  color: var(--primary-text);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app-container {
  padding: 2rem;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2.5rem;
}

.logo {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.logo i {
  font-size: 2.5rem;
  color: var(--accent-color);
}

.logo h1 {
  font-weight: 500;
  font-size: 1.75rem;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background-color: var(--surface-color);
  padding: 0.5rem 1rem;
  border-radius: 99px;
  font-weight: 500;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: #ccc;
  animation: pulse 2s infinite;
}
.dot.online { background-color: var(--green-status); animation-name: pulse-green; }
.dot.offline { background-color: var(--red-status); animation-name: pulse-red; }
.dot.connecting { background-color: var(--orange-status); }

@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(204,169,44, 0.4); } 70% { box-shadow: 0 0 0 10px rgba(204,169,44, 0); } 100% { box-shadow: 0 0 0 0 rgba(204,169,44, 0); } }
@keyframes pulse-green { 0% { box-shadow: 0 0 0 0 var(--green-status); } 70% { box-shadow: 0 0 0 10px rgba(158,206,106,0); } 100% { box-shadow: 0 0 0 0 rgba(158,206,106,0); } }
@keyframes pulse-red { 0% { box-shadow: 0 0 0 0 var(--red-status); } 70% { box-shadow: 0 0 0 10px rgba(247,118,142,0); } 100% { box-shadow: 0 0 0 0 rgba(247,118,142,0); } }


.main-content {
  width: 100%;
}

.full-page-feedback {
    text-align: center;
    padding: 4rem 2rem;
    background-color: var(--surface-color);
    border-radius: 12px;
    border: 2px dashed #414868;
    margin-top: 2rem;
}
.full-page-feedback i {
    font-size: 4rem;
    color: var(--accent-color);
    margin-bottom: 1rem;
    display: inline-block;
}
.full-page-feedback .ph-spinner-gap {
    animation: spin 1s linear infinite;
}
@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}
.full-page-feedback h2 {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
}
.full-page-feedback p {
    color: var(--secondary-text);
}


.device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
}

.device-card {
  background-color: var(--card-color);
  border-radius: 12px;
  padding: 1.5rem;
  border-left: 5px solid var(--secondary-text);
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.device-card.is-on {
    border-left-color: var(--green-status);
}

.device-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 20px rgba(0,0,0,0.2);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.device-icon {
  font-size: 2rem;
  color: var(--accent-color);
}

.device-id {
  font-weight: 500;
  font-size: 1.1rem;
}

.card-body {
  text-align: center;
  flex-grow: 1;
}

.device-status {
  font-size: 2rem;
  font-weight: 700;
  color: white;
}

.card-footer {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.card-footer button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: 'Roboto', sans-serif;
  font-weight: 500;
  font-size: 1rem;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.btn-on {
  background-color: var(--green-status);
  color: var(--bg-color);
}
.btn-on:hover {
  background-color: #b9f27c;
}

.btn-off {
  background-color: var(--red-status);
  color: var(--bg-color);
}
.btn-off:hover {
  background-color: #ff9aa2;
}
</style>