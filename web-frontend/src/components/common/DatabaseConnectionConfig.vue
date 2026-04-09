<template>
  <div class="database-connection-config">
    <div class="config-header">
      <el-icon><Link /></el-icon>
      <span class="config-title">Database Connection Configuration</span>
    </div>
    
    <el-tabs v-model="activeTab" class="database-tabs">
      <!-- MySQL Configuration -->
      <el-tab-pane label="MySQL" name="mysql">
        <el-form ref="mysqlFormRef" :model="mysqlConfig" :rules="mysqlRules" label-position="top">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="Host" prop="host">
                <el-input v-model="mysqlConfig.host" placeholder="localhost" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Port" prop="port">
                <el-input-number v-model="mysqlConfig.port" :min="1" :max="65535" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>
          
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="Database" prop="database">
                <el-input v-model="mysqlConfig.database" placeholder="weibo_prod" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Username" prop="username">
                <el-input v-model="mysqlConfig.username" placeholder="prod_user" />
              </el-form-item>
            </el-col>
          </el-row>
          
          <el-form-item label="Password" prop="password">
            <el-input v-model="mysqlConfig.password" type="password" placeholder="Enter password" show-password />
          </el-form-item>
          
          <el-form-item>
            <div class="connection-actions">
              <el-button
                type="primary"
                :loading="mysqlTesting"
                :aria-label="'Test MySQL connection'"
                @click="testMySQLConnection"
              >
                <el-icon v-if="!mysqlTestResult"><Connection /></el-icon>
                <el-icon v-else-if="mysqlTestResult === 'success'"><CircleCheck /></el-icon>
                <el-icon v-else><CircleClose /></el-icon>
                {{ mysqlTestResult === 'success' ? 'Connected' : mysqlTestResult === 'failed' ? 'Failed' : 'Test Connection' }}
              </el-button>
              
              <el-button
                type="success"
                :disabled="mysqlTestResult !== 'success'"
                :aria-label="'Save MySQL configuration'"
                @click="saveMySQLConfig"
              >
                <el-icon><Check /></el-icon>
                Save Configuration
              </el-button>
            </div>
          </el-form-item>
        </el-form>
      </el-tab-pane>
      
      <!-- HBase Configuration -->
      <el-tab-pane label="HBase" name="hbase">
        <el-form ref="hbaseFormRef" :model="hbaseConfig" :rules="hbaseRules" label-position="top">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="Zookeeper Quorum" prop="quorum">
                <el-input v-model="hbaseConfig.quorum" placeholder="localhost:2181" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Zookeeper Port" prop="zookeeperPort">
                <el-input-number v-model="hbaseConfig.zookeeperPort" :min="1" :max="65535" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>
          
          <el-form-item label="HBase Master" prop="master">
            <el-input v-model="hbaseConfig.master" placeholder="localhost:16000" />
          </el-form-item>
          
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="Table Name" prop="table">
                <el-input v-model="hbaseConfig.table" placeholder="weibo_data" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Column Family" prop="columnFamily">
                <el-input v-model="hbaseConfig.columnFamily" placeholder="cf" />
              </el-form-item>
            </el-col>
          </el-row>
          
          <el-form-item>
            <div class="connection-actions">
              <el-button
                type="primary"
                :loading="hbaseTesting"
                :aria-label="'Test HBase connection'"
                @click="testHBaseConnection"
              >
                <el-icon v-if="!hbaseTestResult"><Connection /></el-icon>
                <el-icon v-else-if="hbaseTestResult === 'success'"><CircleCheck /></el-icon>
                <el-icon v-else><CircleClose /></el-icon>
                {{ hbaseTestResult === 'success' ? 'Connected' : hbaseTestResult === 'failed' ? 'Failed' : 'Test Connection' }}
              </el-button>
              
              <el-button
                type="success"
                :disabled="hbaseTestResult !== 'success'"
                :aria-label="'Save HBase configuration'"
                @click="saveHBaseConfig"
              >
                <el-icon><Check /></el-icon>
                Save Configuration
              </el-button>
            </div>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Link, Connection, CircleCheck, CircleClose, Check
} from '@element-plus/icons-vue'

// Reactive data
const activeTab = ref('mysql')
const mysqlTesting = ref(false)
const hbaseTesting = ref(false)
const mysqlTestResult = ref<'success' | 'failed' | null>(null)
const hbaseTestResult = ref<'success' | 'failed' | null>(null)

// Form refs
const mysqlFormRef = ref()
const hbaseFormRef = ref()

// Configuration data
const mysqlConfig = ref({
  host: 'localhost',
  port: 3306,
  database: 'weibo_prod',
  username: 'prod_user',
  password: ''
})

const hbaseConfig = ref({
  quorum: 'localhost',
  zookeeperPort: 2181,
  master: 'localhost:16000',
  table: 'weibo_data',
  columnFamily: 'cf'
})

// Validation rules
const mysqlRules = {
  host: [
    { required: true, message: 'Please enter MySQL host', trigger: 'blur' }
  ],
  port: [
    { required: true, message: 'Please enter MySQL port', trigger: 'blur' },
    { type: 'number', min: 1, max: 65535, message: 'Port must be between 1 and 65535', trigger: 'blur' }
  ],
  database: [
    { required: true, message: 'Please enter database name', trigger: 'blur' }
  ],
  username: [
    { required: true, message: 'Please enter username', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Please enter password', trigger: 'blur' }
  ]
}

const hbaseRules = {
  quorum: [
    { required: true, message: 'Please enter Zookeeper quorum', trigger: 'blur' }
  ],
  zookeeperPort: [
    { required: true, message: 'Please enter Zookeeper port', trigger: 'blur' },
    { type: 'number', min: 1, max: 65535, message: 'Port must be between 1 and 65535', trigger: 'blur' }
  ],
  master: [
    { required: true, message: 'Please enter HBase master', trigger: 'blur' }
  ],
  table: [
    { required: true, message: 'Please enter table name', trigger: 'blur' }
  ],
  columnFamily: [
    { required: true, message: 'Please enter column family', trigger: 'blur' }
  ]
}

// Methods
const testMySQLConnection = async () => {
  try {
    await mysqlFormRef.value.validate()
    mysqlTesting.value = true
    mysqlTestResult.value = null
    
    // Simulate connection test
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    // Simulate 80% success rate
    const success = Math.random() > 0.2
    
    if (success) {
      mysqlTestResult.value = 'success'
      ElMessage.success('MySQL connection successful')
    } else {
      mysqlTestResult.value = 'failed'
      ElMessage.error('MySQL connection failed: Connection timeout')
    }
  } catch (error) {
    console.error('Validation failed:', error)
  } finally {
    mysqlTesting.value = false
  }
}

const testHBaseConnection = async () => {
  try {
    await hbaseFormRef.value.validate()
    hbaseTesting.value = true
    hbaseTestResult.value = null
    
    // Simulate connection test
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    // Simulate 70% success rate
    const success = Math.random() > 0.3
    
    if (success) {
      hbaseTestResult.value = 'success'
      ElMessage.success('HBase connection successful')
    } else {
      hbaseTestResult.value = 'failed'
      ElMessage.error('HBase connection failed: Zookeeper not reachable')
    }
  } catch (error) {
    console.error('Validation failed:', error)
  } finally {
    hbaseTesting.value = false
  }
}

const saveMySQLConfig = () => {
  ElMessage.success('MySQL configuration saved successfully')
}

const saveHBaseConfig = () => {
  ElMessage.success('HBase configuration saved successfully')
}
</script>

<style scoped>
.database-connection-config {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
  padding: var(--spacing-lg);
  background: var(--color-bg-white);
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
}

.config-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.config-title {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.database-tabs {
  margin-top: var(--spacing-md);
}

.connection-actions {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
}

/* Responsive */
@media (max-width: 768px) {
  .database-connection-config {
    padding: var(--spacing-md);
  }
  
  .connection-actions {
    flex-direction: column;
    align-items: stretch;
  }
  
  .connection-actions .el-button {
    width: 100%;
  }
}
</style>
