'use client';

import { useState } from 'react';

const ICONS = [
  { id: 'workspace', active: true, glyph: 'border' },
  { id: 'screener', active: false, glyph: 'circle' },
  { id: 'alerts', active: false, glyph: 'corner' },
  { id: 'portfolio', active: false, glyph: 'rounded' },
  { id: 'notes', active: false, glyph: 'diamond' },
  { id: 'formula', active: false, glyph: 'line' },
  { id: 'theses', active: false, glyph: 'bubble' },
];

export default function IconRail() {
  const [activeId, setActiveId] = useState('workspace');

  return (
    <div className="w-[52px] bg-white rounded-[20px] shadow-[0_1px_2px_rgba(20,20,25,0.06)] py-2.5 flex flex-col items-center gap-2">
      {ICONS.map((icon, index) => {
        const isActive = icon.id === activeId;
        return (
          <button
            key={icon.id}
            onClick={() => setActiveId(icon.id)}
            className={`w-[34px] h-[34px] rounded-xl flex items-center justify-center transition-colors ${
              isActive ? 'bg-[#f1eeff] shadow-[inset_0_0_0_1px_#ded6ff]' : 'hover:bg-[#f4f3f0]'
            } ${index === 4 ? 'mt-3' : ''}`}
          >
            {icon.glyph === 'border' && (
              <div className={`w-3 h-3 border-[1.6px] rounded-[3px] ${isActive ? 'border-[#5b46d8]' : 'border-[#15161a]'}`} />
            )}
            {icon.glyph === 'circle' && (
              <div className="w-3 h-3 border-[1.6px] border-[#8b8a86] rounded-full" />
            )}
            {icon.glyph === 'corner' && (
              <div className="w-3 h-3 border-s-[1.6px] border-b-[1.6px] border-[#8b8a86]" />
            )}
            {icon.glyph === 'rounded' && (
              <div className="w-3 h-3 border-[1.6px] border-[#8b8a86] rounded-[3px_3px_8px_3px]" />
            )}
            {icon.glyph === 'diamond' && (
              <div className="w-3 h-3 bg-[#8b8a86] rounded-[2px] rotate-45" />
            )}
            {icon.glyph === 'line' && (
              <div className="w-3 h-[3px] bg-[#8b8a86] rounded-[2px]" />
            )}
            {icon.glyph === 'bubble' && (
              <div className="w-3 h-3 border-[1.6px] border-[#8b8a86] rounded-[50%_50%_50%_2px]" />
            )}
          </button>
        );
      })}
    </div>
  );
}
