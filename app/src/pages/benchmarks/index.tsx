import { Nav } from '../../nav';
import { Cover } from './cover';
import { Defs } from './defs';
import { Notes } from './notes';
import { Reel } from './reel';

export function Page() {
  return (
    <>
      <Defs />
      <a className="skip" href="#main">
        Skip to benchmarks
      </a>
      <Nav page="benchmarks" />
      <main id="main">
        <Cover />
        <Reel />
        <Notes />
      </main>
    </>
  );
}
