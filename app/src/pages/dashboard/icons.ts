// Hugeicons as SVG strings, for places React does not render: map images and map markers.
import { BikeIcon, PackageIcon } from '@hugeicons/core-free-icons';
import type { IconSvgElement } from '@hugeicons/react';

interface Paint {
  color: string;
  size: number;
  /** Fill for closed shapes (Hugeicons free icons are outlines). */
  fill?: string;
  /** A white outline underneath, so the icon reads on any map background. */
  halo?: boolean;
  /** Extra markup placed inside <svg> before the icon, e.g. gradient <defs>. */
  defs?: string;
}

const kebab = (key: string) => key.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`);

function shapes(icon: IconSvgElement): string {
  return icon
    .map(([tag, attrs]) => {
      const list = Object.entries(attrs)
        .filter(([key]) => key !== 'key' && key !== 'strokeWidth')
        .map(([key, value]) => `${kebab(key)}="${String(value)}"`);
      return `<${tag} ${list.join(' ')}/>`;
    })
    .join('');
}

export function iconSvg(
  icon: IconSvgElement,
  { color, size, fill = 'none', halo = false, defs = '' }: Paint,
): string {
  const body = shapes(icon);
  const outline = halo ? `<g color="#fff" fill="#fff" stroke-width="4.2">${body}</g>` : '';
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="${size}" height="${size}" fill="none">` +
    `${defs}${outline}<g color="${color}" fill="${fill}" stroke-width="1.7">${body}</g></svg>`
  );
}

// Map images are drawn at twice their display size for sharp edges (registered with pixelRatio 2).
export const MAP_IMAGES = {
  parcel: iconSvg(PackageIcon, {
    color: '#6e4520',
    size: 56,
    halo: true,
    fill: 'url(#box)',
    defs: '<defs><linearGradient id="box" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e3b47a"/><stop offset="1" stop-color="#c38b52"/></linearGradient></defs>',
  }),
  courier: iconSvg(BikeIcon, { color: '#2f6fed', size: 60, halo: true, fill: '#2f6fed1f' }),
};
