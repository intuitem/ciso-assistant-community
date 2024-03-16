import clsx from 'clsx';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';
import Heading from '@theme/Heading';
import CisoBanner from '@site/static/img/banner.png';
import GitHubLogo from '@site/static/img/github-mark-white.png';

import styles from './index.module.css';

function buttonLink(link) {
  window.location.href = link;
}

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--secondary bg-slate-100', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className="hero__title font-sans text-white font-semibold text-6xl">
          {siteConfig.title}
        </Heading>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <a
            className="border-2 py-2 px-5 rounded-lg uppercase text-2xl text-white font-semibold shadow-lg border-primary mt-4 hover:bg-primary hover:text-black transition duration-300 ease-in-out"
            style={{textDecoration: 'none'}}
            href="/docs/intro">
            Get started
          </a>
        </div>
      </div>
    </header>
  );
}

export default function Home(): JSX.Element {
  return (
    <Layout
      title={`End-to-end GRC solution`}
      description="End-to-end GRC solution">
      <main>
        <div className="flex justify-evenly w-full bg-slate-100">
          <img src={CisoBanner} width={800}></img>
          <div className="flex flex-col justify-center items-center">
            <button
              className="border-2 cursor-pointer py-2 px-5 rounded-lg uppercase text-2xl bg-transparent text-indigo-950 font-semibold shadow-lg border-indigo-950 mt-4 hover:bg-indigo-950 hover:text-white transition duration-300 ease-in-out"
              style={{textDecoration: 'none'}}
              onClick={buttonLink.bind(this, '/docs/intro')}>
              Get started
            </button>
            <div className="flex flex-row justify-center items-center">
              <button
                className="py-1 px-3 cursor-pointer mr-1 border-0 rounded-lg text-white bg-indigo-950 font-semibold shadow-lg mt-4 hover:bg-indigo-950 hover:text-white transition duration-300 ease-in-out"
                style={{textDecoration: 'none'}}
                onClick={buttonLink.bind(this, "https://github.com/intuitem/ciso-assistant-community")}>
                  <div className="flex space-x-2 p-1 items-center text-lg">
                    <img className="mr-2" src={GitHubLogo} width={25}></img>
                    Star
                  </div>
              </button>
              <div className="flex flex-row items-center space-x-0">
                <button
                  className="border-0 py-1 px-3 rounded-lg cursor-pointer text-white bg-indigo-950 font-semibold shadow-lg mt-4 hover:bg-indigo-950 hover:text-white transition duration-300 ease-in-out"
                  style={{textDecoration: 'none'}}
                  onClick={buttonLink.bind(this, "https://github.com/intuitem/ciso-assistant-community/stargazers")}>
                    <div className="flex space-x-2 p-1 items-center justify-center text-lg">
                      50+
                    </div>
                </button>
              </div>
            </div>
          </div>
        </div>
        <HomepageFeatures />
      </main>
    </Layout>
  );
}
