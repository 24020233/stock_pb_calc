import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
    baseURL: '/api',
    timeout: 30000
})

http.interceptors.response.use(
    (response) => {
        return response.data
    },
    (error) => {
        ElMessage.error(error.message || 'Request failed')
        return Promise.reject(error)
    }
)

export default http
