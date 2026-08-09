import { useEffect, useRef, useState, useImperativeHandle, forwardRef } from 'react'

export interface WebcamRef {
  captureFrame: () => Promise<Blob | null>
  restartCamera: () => Promise<void>
  stopCamera: () => void
}

interface WebcamPreviewProps {
  onStatusChange?: (statusText: string, isReady: boolean) => void
  onError?: (errorMessage: string) => void
}

export const WebcamPreview = forwardRef<WebcamRef, WebcamPreviewProps>(({ onStatusChange, onError }, ref) => {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const [cameraState, setCameraState] = useState<'idle' | 'starting' | 'ready' | 'permission_denied' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        try {
          track.stop()
        } catch (e) {
          console.warn('Error stopping media track:', e)
        }
      })
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
  }

  const startCamera = async () => {
    stopCamera()
    setCameraState('starting')
    setErrorMessage(null)
    onStatusChange?.('Starting camera...', false)

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      const err = 'Camera access is not supported by this browser.'
      setCameraState('error')
      setErrorMessage(err)
      onError?.(err)
      onStatusChange?.('Camera unsupported', false)
      return
    }

    try {
      const constraints: MediaStreamConstraints = {
        audio: false,
        video: {
          facingMode: 'user',
          width: { ideal: 640, min: 320 },
          height: { ideal: 640, min: 320 },
        },
      }

      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play().catch((playErr) => {
          console.warn('Video play error:', playErr)
        })
      }

      setCameraState('ready')
      onStatusChange?.('Camera ready', true)
    } catch (err: any) {
      console.error('getUserMedia error:', err)
      let displayError = 'Could not access the camera. Please check permissions.'
      let state: 'permission_denied' | 'error' = 'error'

      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        displayError = 'Camera permission was denied. Please allow camera access in your browser.'
        state = 'permission_denied'
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        displayError = 'No camera device was found on this system.'
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        displayError = 'Camera is in use by another application.'
      }

      setCameraState(state)
      setErrorMessage(displayError)
      onError?.(displayError)
      onStatusChange?.(state === 'permission_denied' ? 'Camera permission required' : 'Camera error', false)
    }
  }

  const captureFrame = async (): Promise<Blob | null> => {
    const video = videoRef.current
    const canvas = canvasRef.current

    if (!video || !canvas || cameraState !== 'ready') {
      return null
    }

    const width = video.videoWidth || 640
    const height = video.videoHeight || 480

    canvas.width = width
    canvas.height = height

    const ctx = canvas.getContext('2d')
    if (!ctx) return null

    // Draw video frame to canvas (mirrored horizontally to match selfie preview)
    ctx.translate(width, 0)
    ctx.scale(-1, 1)
    ctx.drawImage(video, 0, 0, width, height)

    // Reset transform
    ctx.setTransform(1, 0, 0, 1, 0, 0)

    return new Promise<Blob | null>((resolve) => {
      canvas.toBlob(
        (blob) => {
          resolve(blob)
        },
        'image/jpeg',
        0.95
      )
    })
  }

  useImperativeHandle(ref, () => ({
    captureFrame,
    restartCamera: startCamera,
    stopCamera,
  }))

  useEffect(() => {
    // Start camera only on component mount
    startCamera()

    return () => {
      // Clean up camera stream on unmount
      stopCamera()
    }
  }, [])

  return (
    <div className="webcam-container">
      <div className="video-viewport">
        <video
          ref={videoRef}
          playsInline
          muted
          className={`webcam-video ${cameraState === 'ready' ? 'active' : 'hidden'}`}
        />

        {/* Biometric Face Guide Overlay */}
        {cameraState === 'ready' && (
          <div className="face-guide-overlay">
            <div className="face-oval-guide">
              <div className="scan-line"></div>
            </div>
            <div className="guide-corner top-left"></div>
            <div className="guide-corner top-right"></div>
            <div className="guide-corner bottom-left"></div>
            <div className="guide-corner bottom-right"></div>
          </div>
        )}

        {/* Loading / Error States */}
        {cameraState === 'starting' && (
          <div className="camera-placeholder starting">
            <div className="spinner large"></div>
            <p className="placeholder-text">Starting camera...</p>
          </div>
        )}

        {(cameraState === 'permission_denied' || cameraState === 'error') && (
          <div className="camera-placeholder error">
            <svg className="error-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
              <line x1="1" y1="1" x2="23" y2="23"></line>
            </svg>
            <p className="placeholder-text">{errorMessage || 'Camera access unavailable'}</p>
            <button
              type="button"
              className="retry-btn"
              onClick={startCamera}
            >
              Grant Permission / Retry
            </button>
          </div>
        )}
      </div>

      {/* Hidden canvas for capturing frame */}
      <canvas ref={canvasRef} style={{ display: 'none' }} />
    </div>
  )
})

WebcamPreview.displayName = 'WebcamPreview'
