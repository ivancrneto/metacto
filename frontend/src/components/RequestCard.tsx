import { timeAgo } from "../format";
import type { FeatureRequest } from "../types";

interface Props {
  request: FeatureRequest;
  currentUser: string;
  onToggleVote: (request: FeatureRequest) => void;
}

export function RequestCard({ request, currentUser, onToggleVote }: Props) {
  const isAuthor = currentUser !== "" && request.author === currentUser;
  const title = isAuthor
    ? "You can't vote on your own request"
    : request.has_voted
      ? "Remove your vote"
      : "Upvote";

  return (
    <li className="card request" style={{ viewTransitionName: `req-${request.id}` }}>
      <button
        className={`vote ${request.has_voted ? "vote--on" : ""}`}
        onClick={() => onToggleVote(request)}
        disabled={isAuthor}
        title={title}
        aria-pressed={request.has_voted}
        aria-label={`${request.vote_count} votes. ${title}`}
      >
        <span className="vote__arrow" aria-hidden="true">
          ▲
        </span>
        <span className="vote__count">{request.vote_count}</span>
      </button>

      <div className="request__body">
        <h3 className="request__title">{request.title}</h3>
        <p className="request__desc">{request.description}</p>
        <p className="muted request__meta">
          by {request.author} · {timeAgo(request.created_at)}
        </p>
      </div>
    </li>
  );
}
