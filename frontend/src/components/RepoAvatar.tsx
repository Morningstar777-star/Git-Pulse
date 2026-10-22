import React, { useState } from 'react';

interface RepoAvatarProps {
  owner: string;
  name: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function getAvatarColor(name: string): string {
  const colors = [
    'bg-blue-600 text-white',
    'bg-purple-600 text-white',
    'bg-emerald-600 text-white',
    'bg-amber-600 text-white',
    'bg-rose-600 text-white',
    'bg-indigo-600 text-white',
    'bg-cyan-600 text-white',
    'bg-teal-600 text-white'
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

export const RepoAvatar: React.FC<RepoAvatarProps> = ({
  owner,
  name,
  size = 'md',
  className = ''
}) => {
  const [hasError, setHasError] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);

  const initial = (name[0] || owner[0] || 'R').toUpperCase();
  const avatarBg = getAvatarColor(name || owner);

  // Pixel sizes for GitHub avatar query
  const pxSize = size === 'lg' ? 128 : 64;

  const sizeClasses = {
    sm: 'w-6 h-6 rounded text-[11px]',
    md: 'w-7 h-7 rounded-md text-xs',
    lg: 'w-11 h-11 rounded-xl text-base'
  }[size];

  // If no owner or image failed, render letter monogram
  if (!owner || hasError) {
    return (
      <div 
        className={`${sizeClasses} ${avatarBg} font-bold font-mono flex items-center justify-center shrink-0 shadow-sm ${className}`}
        aria-hidden="true"
      >
        {initial}
      </div>
    );
  }

  return (
    <div 
      className={`relative ${sizeClasses} shrink-0 overflow-hidden bg-slate-100 dark:bg-[#21262d] flex items-center justify-center border border-black/5 dark:border-white/10 shadow-sm ${className}`}
      aria-hidden="true"
    >
      {/* Background initial tile while image is loading */}
      {!isLoaded && (
        <div className={`absolute inset-0 ${avatarBg} font-bold font-mono flex items-center justify-center`}>
          {initial}
        </div>
      )}

      {/* Real GitHub Logo / Avatar */}
      <img
        src={`https://github.com/${owner}.png?size=${pxSize}`}
        alt={owner}
        loading="lazy"
        onLoad={() => setIsLoaded(true)}
        onError={() => setHasError(true)}
        className={`w-full h-full object-cover transition-opacity duration-200 ${
          isLoaded ? 'opacity-100' : 'opacity-0'
        }`}
      />
    </div>
  );
};
