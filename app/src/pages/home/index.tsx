import { Nav } from '../../nav';
import { Defs } from './defs';
import { Hero } from './hero';
import { Story } from './story';
import { Quality } from './quality';
import { Voices } from './voices';

export function Page() {
  return (
    <>
      <Defs />
      <a className="skip" href="#main">
        Skip to Hermes
      </a>
      <Nav page="home" />
      <main id="main">
        <Hero />
        <Story />
        <Quality />
        <Voices />
      </main>
    </>
  );
}
