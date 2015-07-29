(function() {
  $.ajaxSetup({contentType: 'application/json'});
  var errorTimeout;

  function showError(resp) {
    var msg;
    if (!resp) {
      msg = "Request failed";
      return true;
    }
    else if (!resp.result || !resp.result.error) return false;
    else msg = resp.result.error;

    $('#error-box-inner').text(msg);

    clearTimeout(errorTimeout);
    $('#error-box').show();
    errorTimeout = setTimeout(function() {
      $('#error-box').hide();
    }, 4000);
    return true;
  }

  function makeId() {
    var text = "";
    var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";

    for( var i=0; i < 20; i++ )
      text += possible.charAt(Math.floor(Math.random() * possible.length));

    return text;
  }

  var AvailableGames = React.createClass({
    getInitialState: function() { return {games: []} },

    componentDidMount: function() {
      var self = this;
      $.get('/list', function(r) { self.setState(r); });
    },

    handleClick: function(game) {
      this.props.joinFunc(game);
    },

    render: function() {
      var self = this;
      return (
        <div id="games-list">
          <h2>Available Games</h2>
          <ul>
            {this.state.games.map(function(g) {
              return (
                <li key={g.uuid}>
                  <span
                    onClick   = {self.handleClick.bind(self, g.uuid)}
                    className = "game-title"
                  >
                    {g.title}
                  </span>
                  <span className="game-playerCount">
                    ({g.players} players)
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      );
    }
  });

  var Card = React.createClass({
    getInitialState: function() {
      return {
        used: false,
      }
    },

    onHover: function() {
      var uuid = this.props.card.uuid;
      $("#expand-info").html($("#" + uuid).html());
    },

    doCard: function() {
      if (this.state.used) return;
      if (this.props.callback(this.props.type, this.props.card)) {
        this.setState({
          used: true,
        })
      }
    },

    render: function() {
      var card = this.props.card;
      var type = null;

      switch(card.type) {
        case 'Action - Reaction':
          type = 'reaction';
          break;
        case 'Action - Attack':
          type = 'attack';
          break;
        case 'Action - Victory':
          type = 'actionVictory';
          break;
        case 'Action - Duration':
          type = 'duration';
          break;
        default:
          type = card.type.toLowerCase();
      }
      type = "card " + type;
      var usage = (this.state.used ? "used" : "unused")

      return (
        <div className="supply-item">
          <div
            onClick     = {this.doCard}
            id          = {card.uuid}
            className   = {type}
            onMouseOver = {this.onHover}
            data-used   = {usage}
          >
            <div className="header">
              <div className="value">
                {card.value > 0 && '$' + card.value}
              </div>
              <div className="name">
                {card.name}
              </div>
            </div>
            <div className="vp">
              { card.points > 0 &&
                <div className="points">
                  {card.points} VP
                </div>
              }
            </div>
            <div className="footer">
              <div className="cost">
                {card.cost}
              </div>
              <div className="type">
                {card.type}
              </div>
            </div>
            <div className="text">
              {card.text.map(function(line) {
                if(line == '------') {
                  return (
                    <div className="divider"></div>
                  )
                } else {
                  return (
                    <div className="line">{line}</div>
                  )
                }
              })}
            </div>
          </div>
          { this.props.remaining != null &&
            <div className="cards-left">
              { this.props.remaining }
            </div>
          }
        </div>
      );
    }
  });

  var Supply = React.createClass({
    render: function() {
      var self = this;
      var cards = this.props.supply.map(function(cardSet) {
        return (
          <Card
            key       = {cardSet.card.uuid}
            callback  = {self.props.callback}
            type      = "supply"
            card      = {cardSet.card}
            remaining = {cardSet.left}
          />
        );
      });
      return (
        <div id="supply">
          {cards}
        </div>
      );
    }
  });

  var CardList = React.createClass({
    render: function() {
      var cards = [];
      var self = this;
      if (this.props.cards) {
        cards = this.props.cards.map(function(card) {
          return (
              <Card
                key      = {card.uuid}
                callback = {self.props.callback}
                type     = {self.props.name}
                card     = {card}
              />
          )
        });
      }
      return (
        <div id={this.props.name}>
          <div className="cards-inner">
            {cards}
          </div>
        </div>
      );
    }
  });

  var Game = React.createClass({
    getInitialState: function() {
      return {
        supply: [],
        hand: [],
        discard: [],
        inPlay: [],
        actions: 1,
        buys: 1,
        money: 0,
        turn: -1,
        phase: "pregame",
        mode: "normal",
        refresher: makeId(),
      };
    },

    cancelTarget: function() {
      this.setState({
        mode: "normal",
        targets: null,
        activeCard: null,
        picked: [],
        refresher: makeId(),
      });
    },

    finishTarget: function() {
      if (this.state.activeCard == "Forge") {
        this.setState({
          targets: 1,
        });
      } else {
        this.doCard("finish", this.state.activeCard);
      }
    },

    doCard: function(type, card) {
      var self = this;
      var action = "/play/";
      var pid = this.props.pid;
      var uuid = this.props.uuid;
      var payload = {};

      if (this.state.mode == "target") {
        var numTargets = this.state.targets;
        var cards = this.state.picked;
        if (type != "finish") {
          cards.push(card);
          numTargets--;
        }
        if (numTargets == 0 || type == "finish") {
          switch (this.state.activeCard.name) {
            case "Bishop":
            case "TradeRoute":
            case "Mint":
              payload = {card: card};
              break;
            case "Remodel":
            case "Mine":
            case "Expand":
              payload = {trash: cards[0], gain: cards[1]};
              break;
            case "Workshop":
            case "Feast":
              payload = {gain: card};
              break;
            case "Cellar":
            case "Chapel":
              payload = {cards: cards};
              console.log(payload);
              break;
            case "Forge":
              payload = {cards: cards.slice(0, -1), gain: cards[-1]};
              break;
            case "CountingHouse":
              pyaload = {count: cards.length};
              break;
          }
          this.cancelTarget();
        } else {
          this.setState({
            targets: numTargets,
            picked: cards,
          });
          return true;
        }
      } else if (this.state.mode == "normal") {
        if (type != "hand" && type != "supply") {
          return false;
        }
        if (type == "supply") action = "/buy/";

        if (type == "hand") {
          var numTargets = 0;
          switch (card.name) {
            case "Bishop":
            case "TradeRoute":
            case "Mint":
            case "Workshop":
            case "Feast":
              numTargets: 1;
            case "Remodel":
            case "Mine":
            case "Expand":
              if (numTargets == 0) numTargets = 2;
            case "Cellar":
            case "Chapel":
            case "Forge":
            case "CountingHouse":
              if (numTargets == 0) numTargets = -1;
              this.setState({
                mode: "target",
                targets: numTargets,
                activeCard: card,
                picked: [],
              });
              return true;
          }
        }
      }

      $.post(
        '/game/' + this.props.gid + action + card.name + this.loginArgs(),
        JSON.stringify(payload),
        function(resp) {
          if (!showError(resp)) self.updateState(resp);
        }
      );

      return true;
    },

    updateState: function(r) {
      if (r.state) {
        this.setState({
          supply: r.state.supply,
          hand: r.state.deck.hand,
          discard: r.state.deck.discard,
          inPlay: r.state.deck.in_play,
          actions: r.state.actions,
          buys: r.state.buys,
          money: r.state.money,
          turn: r.state.turn,
          phase: r.state.state,
          refresher: makeId(),
        });
      }
    },

    loginArgs: function() {
      return '?pid=' + this.props.pid + '&uuid=' + this.props.uuid;
    },

    nextPhase: function() {
      var self = this;
      this.request = $.post(
        '/game/' + this.props.gid + '/next_phase' + this.loginArgs(),
        function(resp) {
          if (!showError(resp)) self.updateState(resp);
        }
      );
    },

    poll: function() {
      var self = this;
      this.request = $.get(
        '/poll/' + this.props.gid + this.loginArgs(),
        function(resp) {
          if (!showError(resp)) {
            self.updateState(resp);
            self.poll();
          }
        }
      );
    },

    stat: function() {
      var self = this;
      $.get(
        '/stat/' + this.props.gid + this.loginArgs(),
        function(resp) {
          if (!showError(resp)) self.updateState(resp);
        }
      );
    },

    componentDidMount: function() {
      this.stat();
      this.poll();
    },

    componentWillUnmount: function() {
      this.request.abort();
    },

    render: function() {
      var mode = this.state.mode;
      var msg = "";
      var targets = 0;
      if (mode == "target") {
        targets = this.state.targets;
        switch (this.state.activeCard.name) {
          case "CountingHouse":
            msg = "Choose coppers from discard to retrieve";
            break;
          case "Bishop":
          case "TradeRoute":
            msg = "Choose card from hand to trash";
            break;
          case "Mint":
            msg = "Choose treasure from hand to copy";
            break;
          case "Remodel":
          case "Mine":
          case "Expand":
            if (targets == 2) msg = "Choose card in hand to trash";
            else msg = "Choose card from supply to gain";
            break;
          case "Workshop":
          case "Feast":
            msg = "Choose card from supply to gain";
            break;
          case "Forge":
            if (targets == 1) msg = "Choose card from supply to gain";
            else msg = "Choose card in hand to trash";
            break;
          case "Cellar":
            msg = "Choose card in hand to discard";
            break;
          case "Chapel":
            msg = "Choose card in hand to trash";
            break;
        }
      }

      return (
        <div id="container" key={this.state.refresher}>
          <div id="card-area">
            <Supply supply={this.state.supply} callback={this.doCard}/>
            <div className="breaker"></div>
          </div>
          <div id="expand-info"></div>
          <div id="inplay-popup">
            <div className="popup-bar" id="inplay-bar">
              <img src="client/img/inplay.png" />
            </div>
            <CardList cards={this.state.inPlay} callback={this.doCard} name="inplay" />
          </div>
          <div id="discard-popup">
            <div className="popup-bar" id="discard-bar">
              <img src="client/img/trash.png" />
            </div>
            <CardList cards={this.state.discard} callback={this.doCard} name="discard" />
          </div>
          <div id="hand-wrapper">
            <CardList cards={this.state.hand} callback={this.doCard} name="hand" />
          </div>
          <div id="status-window">
            <div id={"n-a-" + this.state.phase} className="status-box">
              <span className="status-label">A</span> {this.state.actions}
            </div>
            <div id={"n-b-" + this.state.phase} className="status-box">
              <span className="status-label">B</span> {this.state.buys}
            </div>
            <div id="n-m" className="status-box">
              <span className="status-label">$</span> {this.state.money}
            </div>
            <div id="next-phase" className="status-box" onClick={this.nextPhase}>
              &#x25b8;
            </div>
          </div>
          <div className="breaker"></div>
          <div id="error-box"><div id="error-box-inner"></div></div>
          { mode == "target" &&
            <div id="info-box">
              <div id="info-box-inner">
                {msg}
                {targets < 0 &&
                  <button className="info-button" onClick={this.finishTarget}>
                    Finish
                  </button>
                }
                <button className="info-button" onClick={this.cancelTarget}>
                  Cancel
                </button>
              </div>
            </div>
          }
        </div>
      );
    }
  });

  var GameCreator = React.createClass({
    join: function(game) {
      var self = this;
      $.post('/join/' + game, function(resp) {
        if (!showError(resp)) {
          self.setState({
            joined: true,
            pid: resp.id,
            uuid: resp.uuid,
            gid: game,
          });
          self.save();
        }
      });
    },

    submit: function(evt) {
      evt.preventDefault();
      var self = this;
      $.post('/create', JSON.stringify(this.state), function(game) {
        self.join(game.game);
        self.setState({startKey: game.start});
      });
    },

    componentDidMount: function() {
      var session = window.localStorage.getItem('session');
      if (session === null) return;
      session = JSON.parse(session);
      this.setState(session);
    },

    getInitialState: function() {
      return {
        title: 'My cool game!',
        joined: false,
      };
    },

    handleChange: function(event) {
      this.setState({title: event.target.value});
    },

    save: function() {
      var self = this;
      setTimeout(function() {
        window.localStorage['session'] = JSON.stringify(self.state);
      }, 500);
    },

    leaveGame: function() {
      this.setState({joined: false});
      this.save();
    },

    startGame: function() {
      var self = this;
      $.post('/start/' + this.state.gid + '/' + this.state.startKey, function(resp) {
        if (!showError(resp)) {
          self.setState({startKey: null});
          self.save();
        }
      });
    },

    render: function() {
      if (this.state.joined) {
        return (
          <div id="game">
            <div id="game-title">
              <span id="game-title-span">{this.state.title}</span>
              <button id="leave-game" onClick={this.leaveGame}>Leave</button>
              { this.state.startKey &&
                <button id="start-game" onClick={this.startGame}>Start</button>
              }
            </div>
            <Game gid={this.state.gid} pid={this.state.pid} uuid={this.state.uuid} />
          </div>
        );
      } else {
        return (
          <div id="game-manager">
            <h1 id="title">Let's play dominion!</h1>
            <AvailableGames joinFunc={this.join} />
            <div id="create-game">
              <h2>New Game</h2>
              <form onSubmit={this.submit}>
                <div>
                  <input
                    type     = "text"
                    name     = "title"
                    value    = {this.state.title}
                    onChange = {this.handleChange} />
                </div>
                <div>
                  <input type="submit" value="Let's play!" />
                </div>
              </form>
            </div>
            <div id="error-box"><div id="error-box-inner"></div></div>
          </div>
        );
      }
    }
  });

  React.render(
    (
      <div>
        <GameCreator />
      </div>
    ),
    document.getElementById('content')
  );
})();
