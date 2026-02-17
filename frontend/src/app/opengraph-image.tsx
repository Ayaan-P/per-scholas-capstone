import { ImageResponse } from 'next/og'

export const runtime = 'edge'
export const alt = 'FundFish - AI Fundraising for Nonprofits'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          background: 'linear-gradient(135deg, #1e3a5f 0%, #0f2439 100%)',
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'system-ui, sans-serif',
        }}
      >
        {/* Wave pattern overlay */}
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            height: 200,
            background: 'linear-gradient(180deg, transparent 0%, rgba(59, 130, 246, 0.1) 100%)',
          }}
        />
        
        {/* Fish icon and logo */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            marginBottom: 40,
          }}
        >
          <span style={{ fontSize: 80 }}>🐟</span>
          <span
            style={{
              fontSize: 72,
              fontWeight: 700,
              color: '#ffffff',
              marginLeft: 20,
              letterSpacing: '-2px',
            }}
          >
            FundFish
          </span>
        </div>
        
        {/* Tagline */}
        <div
          style={{
            fontSize: 36,
            color: '#94a3b8',
            marginBottom: 50,
            textAlign: 'center',
            maxWidth: 800,
          }}
        >
          AI-Powered Fundraising for Nonprofits
        </div>
        
        {/* Features */}
        <div
          style={{
            display: 'flex',
            gap: 50,
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              color: '#3b82f6',
              fontSize: 24,
            }}
          >
            <span style={{ marginRight: 10 }}>✨</span>
            Grant Discovery
          </div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              color: '#3b82f6',
              fontSize: 24,
            }}
          >
            <span style={{ marginRight: 10 }}>📝</span>
            Proposal Writing
          </div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              color: '#3b82f6',
              fontSize: 24,
            }}
          >
            <span style={{ marginRight: 10 }}>🎯</span>
            Smart Matching
          </div>
        </div>
        
        {/* URL */}
        <div
          style={{
            position: 'absolute',
            bottom: 40,
            right: 50,
            fontSize: 22,
            color: '#64748b',
          }}
        >
          fundfish.pro
        </div>
      </div>
    ),
    {
      ...size,
    }
  )
}
