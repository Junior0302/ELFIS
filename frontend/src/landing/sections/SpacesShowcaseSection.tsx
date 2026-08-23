import type { CSSProperties } from 'react'
import { WorkspaceSpaceIcon } from '../../workspaces/WorkspaceSpaceIcon'
import '../../workspaces/workspace-space-icon.css'
import { SectionCopy } from '../components/SectionCopy'
import { LANDING_SPACE_STORIES, LANDING_SPACES } from '../landing.copy'
import { PUBLIC_OPEN_SPACES } from '../landing.model'

export function SpacesShowcaseSection() {
  return (
    <section
      id="espaces"
      className="landing-block landing-block--plain"
      aria-labelledby="landing-spaces-title"
    >
      <div className="landing-block__inner">
        <p className="landing-kicker">{LANDING_SPACES.eyebrow}</p>
        <h2 id="landing-spaces-title">{LANDING_SPACES.title}</h2>
        <p className="landing-section__lead">{LANDING_SPACES.lead}</p>
        <p className="landing-section__lead">{LANDING_SPACES.close}</p>
        <div className="landing-space-stories">
          {PUBLIC_OPEN_SPACES.map((space) => {
            const story = LANDING_SPACE_STORIES[space.id]
            return (
              <article
                key={space.id}
                id={`espace-${space.id}`}
                className="landing-space-story"
                style={
                  {
                    '--space-accent': space.accent,
                    '--space-soft': space.accentSoft,
                  } as CSSProperties
                }
              >
                <div className="landing-space-story__head">
                  <WorkspaceSpaceIcon
                    icon={space.icon}
                    accent={space.accent}
                    soft={space.accentSoft}
                  />
                  <div>
                    <p className="landing-space-story__label">{space.label}</p>
                    <h3>{story.title}</h3>
                  </div>
                </div>
                <div className="landing-prose">
                  <SectionCopy paragraphs={story.paragraphs} />
                </div>
              </article>
            )
          })}
        </div>
      </div>
    </section>
  )
}
