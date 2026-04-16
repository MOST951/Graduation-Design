import { ElMessage, ElNotification } from 'element-plus'

// Error types
export enum ErrorType {
  NETWORK = 'network',
  VALIDATION = 'validation',
  PERMISSION = 'permission',
  NOT_FOUND = 'not_found',
  SERVER = 'server',
  UNKNOWN = 'unknown'
}

// Error severity levels
export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

// Error interface
export interface AppError {
  type: ErrorType
  severity: ErrorSeverity
  message: string
  code?: string | number
  details?: any
  timestamp: Date
  userMessage?: string
  action?: string
}

// Error handler class
export class ErrorHandler {
  private static instance: ErrorHandler
  private errorLog: AppError[] = []
  private maxLogSize = 100

  static getInstance(): ErrorHandler {
    if (!ErrorHandler.instance) {
      ErrorHandler.instance = new ErrorHandler()
    }
    return ErrorHandler.instance
  }

  // Handle API errors
  handleApiError(error: any, context?: string): AppError {
    const appError: AppError = {
      type: this.getErrorType(error),
      severity: this.getErrorSeverity(error),
      message: error.message || 'Unknown error occurred',
      code: error.code || error.status,
      details: error,
      timestamp: new Date(),
      userMessage: this.getUserMessage(error),
      action: this.getSuggestedAction(error)
    }

    this.logError(appError)
    this.notifyUser(appError, context)
    return appError
  }

  // Handle async operation errors
  async handleAsyncError<T>(
    operation: () => Promise<T>,
    context?: string,
    options?: {
      showLoading?: boolean
      customErrorHandler?: (error: any) => void
    }
  ): Promise<T | null> {
    try {
      if (options?.showLoading) {
        ElMessage({
          message: 'Processing...',
          type: 'info',
          duration: 0
        })
      }

      const result = await operation()
      
      if (options?.showLoading) {
        ElMessage.closeAll()
        ElMessage({
          message: 'Operation completed successfully',
          type: 'success',
          duration: 2000
        })
      }

      return result
    } catch (error) {
      if (options?.customErrorHandler) {
        options.customErrorHandler(error)
      } else {
        this.handleApiError(error, context)
      }
      
      if (options?.showLoading) {
        ElMessage.closeAll()
      }
      
      return null
    }
  }

  // Handle form validation errors
  handleValidationError(errors: Record<string, string[]>): void {
    const errorMessages = Object.entries(errors)
      .flatMap(([field, messages]) => messages.map(msg => `${field}: ${msg}`))
      .join('; ')

    const appError: AppError = {
      type: ErrorType.VALIDATION,
      severity: ErrorSeverity.MEDIUM,
      message: 'Validation failed',
      details: errors,
      timestamp: new Date(),
      userMessage: 'Please check your input and try again',
      action: 'Review form fields and correct errors'
    }

    this.logError(appError)
    ElMessage({
      message: errorMessages || 'Please check your input and try again',
      type: 'warning',
      duration: 5000
    })
  }

  // Get error type from HTTP status or error object
  private getErrorType(error: any): ErrorType {
    if (error.response) {
      const status = error.response.status
      if (status === 404) return ErrorType.NOT_FOUND
      if (status === 403 || status === 401) return ErrorType.PERMISSION
      if (status >= 500) return ErrorType.SERVER
      if (status >= 400) return ErrorType.VALIDATION
    }
    
    if (error.code === 'NETWORK_ERROR' || error.message?.includes('network')) {
      return ErrorType.NETWORK
    }

    return ErrorType.UNKNOWN
  }

  // Get error severity
  private getErrorSeverity(error: any): ErrorSeverity {
    const type = this.getErrorType(error)
    
    switch (type) {
      case ErrorType.SERVER:
        return ErrorSeverity.HIGH
      case ErrorType.NETWORK:
        return ErrorSeverity.MEDIUM
      case ErrorType.PERMISSION:
        return ErrorSeverity.HIGH
      case ErrorType.NOT_FOUND:
        return ErrorSeverity.LOW
      case ErrorType.VALIDATION:
        return ErrorSeverity.MEDIUM
      default:
        return ErrorSeverity.MEDIUM
    }
  }

  // Get user-friendly message
  private getUserMessage(error: any): string {
    const type = this.getErrorType(error)
    
    switch (type) {
      case ErrorType.NETWORK:
        return 'Network connection error. Please check your internet connection.'
      case ErrorType.PERMISSION:
        return 'You don\'t have permission to perform this action.'
      case ErrorType.NOT_FOUND:
        return 'The requested resource was not found.'
      case ErrorType.SERVER:
        return 'Server error occurred. Please try again later.'
      case ErrorType.VALIDATION:
        return 'Please check your input and try again.'
      default:
        return 'An unexpected error occurred. Please try again.'
    }
  }

  // Get suggested action
  private getSuggestedAction(error: any): string {
    const type = this.getErrorType(error)
    
    switch (type) {
      case ErrorType.NETWORK:
        return 'Check internet connection and retry'
      case ErrorType.PERMISSION:
        return 'Contact administrator for access'
      case ErrorType.NOT_FOUND:
        return 'Verify the resource exists'
      case ErrorType.SERVER:
        return 'Wait a moment and retry'
      case ErrorType.VALIDATION:
        return 'Review and correct form fields'
      default:
        return 'Try again or contact support'
    }
  }

  // Log error for debugging
  private logError(error: AppError): void {
    this.errorLog.unshift(error)
    
    // Keep log size manageable
    if (this.errorLog.length > this.maxLogSize) {
      this.errorLog = this.errorLog.slice(0, this.maxLogSize)
    }

    // Console logging for development
    if (import.meta.env.DEV) {
      console.error('App Error:', error)
    }
  }

  // Notify user based on severity
  private notifyUser(error: AppError, context?: string): void {
    const message = context ? `${context}: ${error.userMessage}` : error.userMessage
    
    switch (error.severity) {
      case ErrorSeverity.LOW:
        ElMessage({
          message,
          type: 'info',
          duration: 3000
        })
        break
        
      case ErrorSeverity.MEDIUM:
        ElMessage({
          message,
          type: 'warning',
          duration: 5000
        })
        break
        
      case ErrorSeverity.HIGH:
        ElNotification({
          title: '提示',
          message,
          type: 'warning',
          duration: 5000,
          description: error.action
        })
        break
        
      case ErrorSeverity.CRITICAL:
        ElNotification({
          title: '系统提示',
          message,
          type: 'warning',
          duration: 8000,
          description: `Action: ${error.action}`
        })
        break
    }
  }

  // Get error log
  getErrorLog(): AppError[] {
    return [...this.errorLog]
  }

  // Clear error log
  clearErrorLog(): void {
    this.errorLog = []
  }

  // Export error log for debugging
  exportErrorLog(): string {
    return JSON.stringify(this.errorLog, null, 2)
  }
}

// Export singleton instance
export const errorHandler = ErrorHandler.getInstance()

// Utility functions for common patterns
export const withErrorHandling = async <T>(
  operation: () => Promise<T>,
  context?: string,
  options?: {
    showLoading?: boolean
    customErrorHandler?: (error: any) => void
  }
): Promise<T | null> => {
  return errorHandler.handleAsyncError(operation, context, options)
}

// HOC for Vue components
export const withAsyncErrorHandling = (
  asyncFn: () => Promise<any>,
  context?: string
) => {
  return errorHandler.handleAsyncError(asyncFn, context)
}
