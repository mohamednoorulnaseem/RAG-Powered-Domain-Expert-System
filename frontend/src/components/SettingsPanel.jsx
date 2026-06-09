/**
 * SettingsPanel.jsx — Right Collapsible Panel
 *
 * Controls:
 *  - OpenAI API key input (password field, session-only)
 *  - Model selector (gpt-4o, gpt-4o-mini)
 *  - Chunk size slider (500–2000)
 *  - Top-K retrieval slider (1–10)
 *  - Temperature slider (0–1)
 *
 * All settings are stored in parent state, never persisted.
 */

import {
  HiXMark,
  HiOutlineKey,
  HiOutlineCpuChip,
  HiOutlineAdjustmentsHorizontal,
  HiOutlineEye,
  HiOutlineEyeSlash,
} from 'react-icons/hi2'
import { useState } from 'react'

function SettingsPanel({ settings, onSettingsChange, onClose }) {
  const [showApiKey, setShowApiKey] = useState(false)

  const updateSetting = (key, value) => {
    onSettingsChange(prev => ({ ...prev, [key]: value }))
  }

  return (
    <div className="flex flex-col h-full w-80">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border">
        <div className="flex items-center gap-2">
          <HiOutlineAdjustmentsHorizontal className="text-accent" size={20} />
          <h2 className="text-base font-semibold text-text-primary">Settings</h2>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-bg-hover transition-colors"
          id="close-settings-btn"
        >
          <HiXMark size={18} />
        </button>
      </div>

      {/* Settings Content */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-6">

        {/* ── API Key ──────────────────────────────────── */}
        <div className="animate-fade-in">
          <label className="flex items-center gap-2 text-sm font-medium text-text-primary mb-2">
            <HiOutlineKey size={16} className="text-accent" />
            OpenAI API Key
          </label>
          <div className="relative">
            <input
              type={showApiKey ? 'text' : 'password'}
              value={settings.apiKey}
              onChange={(e) => updateSetting('apiKey', e.target.value)}
              placeholder="sk-..."
              className="w-full px-3 py-2.5 pr-10 rounded-xl bg-bg-tertiary border border-border text-sm text-text-primary placeholder-text-muted outline-none focus:border-accent/50 transition-colors"
              id="api-key-input"
            />
            <button
              type="button"
              onClick={() => setShowApiKey(!showApiKey)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary transition-colors"
            >
              {showApiKey ? <HiOutlineEyeSlash size={16} /> : <HiOutlineEye size={16} />}
            </button>
          </div>
          <p className="text-xs text-text-muted mt-1.5">
            Stored in session only — never saved to disk.
          </p>
        </div>

        {/* ── Model Selector ───────────────────────────── */}
        <div className="animate-fade-in" style={{ animationDelay: '50ms' }}>
          <label className="flex items-center gap-2 text-sm font-medium text-text-primary mb-2">
            <HiOutlineCpuChip size={16} className="text-accent" />
            Model
          </label>
          <div className="grid grid-cols-2 gap-2">
            {[
              { value: 'gpt-4o', label: 'GPT-4o', desc: 'Most capable' },
              { value: 'gpt-4o-mini', label: 'GPT-4o Mini', desc: 'Faster' },
            ].map(model => (
              <button
                key={model.value}
                onClick={() => updateSetting('model', model.value)}
                className={`px-3 py-2.5 rounded-xl text-left transition-all duration-200 border ${
                  settings.model === model.value
                    ? 'bg-accent/10 border-accent/40 text-accent'
                    : 'bg-bg-tertiary border-border text-text-secondary hover:border-border-light'
                }`}
                id={`model-${model.value}`}
              >
                <p className="text-sm font-medium">{model.label}</p>
                <p className="text-xs opacity-60 mt-0.5">{model.desc}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="h-px bg-border" />

        {/* ── Chunk Size Slider ────────────────────────── */}
        <div className="animate-fade-in" style={{ animationDelay: '100ms' }}>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-text-primary">
              Chunk Size
            </label>
            <span className="text-xs font-mono px-2 py-0.5 rounded-md bg-bg-tertiary text-accent">
              {settings.chunkSize}
            </span>
          </div>
          <input
            type="range"
            min={500}
            max={2000}
            step={100}
            value={settings.chunkSize}
            onChange={(e) => updateSetting('chunkSize', parseInt(e.target.value))}
            className="w-full"
            id="chunk-size-slider"
          />
          <div className="flex justify-between text-xs text-text-muted mt-1">
            <span>500</span>
            <span>2000</span>
          </div>
          <p className="text-xs text-text-muted mt-1">
            Characters per chunk. Smaller = more precise, larger = more context.
          </p>
        </div>

        {/* ── Top-K Slider ─────────────────────────────── */}
        <div className="animate-fade-in" style={{ animationDelay: '150ms' }}>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-text-primary">
              Top-K Results
            </label>
            <span className="text-xs font-mono px-2 py-0.5 rounded-md bg-bg-tertiary text-accent">
              {settings.topK}
            </span>
          </div>
          <input
            type="range"
            min={1}
            max={10}
            step={1}
            value={settings.topK}
            onChange={(e) => updateSetting('topK', parseInt(e.target.value))}
            className="w-full"
            id="top-k-slider"
          />
          <div className="flex justify-between text-xs text-text-muted mt-1">
            <span>1</span>
            <span>10</span>
          </div>
          <p className="text-xs text-text-muted mt-1">
            Number of most similar chunks to retrieve for context.
          </p>
        </div>

        {/* ── Temperature Slider ───────────────────────── */}
        <div className="animate-fade-in" style={{ animationDelay: '200ms' }}>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-text-primary">
              Temperature
            </label>
            <span className="text-xs font-mono px-2 py-0.5 rounded-md bg-bg-tertiary text-accent">
              {settings.temperature.toFixed(1)}
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={1}
            step={0.1}
            value={settings.temperature}
            onChange={(e) => updateSetting('temperature', parseFloat(e.target.value))}
            className="w-full"
            id="temperature-slider"
          />
          <div className="flex justify-between text-xs text-text-muted mt-1">
            <span>0 (Precise)</span>
            <span>1 (Creative)</span>
          </div>
          <p className="text-xs text-text-muted mt-1">
            Lower = deterministic answers. Higher = more varied responses.
          </p>
        </div>

        <div className="h-px bg-border" />

        {/* ── Info ──────────────────────────────────────── */}
        <div className="animate-fade-in" style={{ animationDelay: '250ms' }}>
          <div className="p-3 rounded-xl bg-accent-dim border border-accent/10">
            <p className="text-xs text-accent/80 leading-relaxed">
              <strong className="text-accent">Tip:</strong> Changes to chunk size only affect newly uploaded documents.
              Existing documents keep their original chunking.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SettingsPanel
